# Interlock — Design Spec

> A runtime circuit breaker for autonomous AI agents. It sits between an agent and its
> tools and **halts irreversible, out-of-intent actions** while letting benign work flow.
> The enforcement gate is **deterministic policy-as-code, not another LLM.**

- **Hackathon:** OpenAI Build Week — **Developer Tools** track
- **Build environment:** OpenAI Codex + GPT-5.6 (solo, ~6 days)
- **Deadline:** 2026-07-21 17:00 PT

---

## 1. The problem (validated)

Autonomous agents take irreversible real-world actions and get them wrong: a Replit agent
deleted a production database after being told not to; a Cursor agent ran `rm -rf` right
after "DO NOT RUN ANYTHING"; EchoLeak (CVE-2025-32711) made Copilot exfiltrate files from a
single email. Gartner: **trust, not capability, blocks deployment** — only 15% of orgs will
run fully-autonomous agents, and through 2028 **≥80% of unauthorized agent actions come from
the agent's own misbehavior, not attackers.** This makes the problem one of *intent
reconciliation*, not malware detection.

## 2. The thesis (the differentiator)

Three claims, each a deliberate departure from existing guardrail products:

1. **Intent, not content.** We do not ask "is this text malicious." We ask "does this action
   match what the human actually asked for?" — a machine-checkable policy compiled from the
   task.
2. **Keep known reads frictionless; fail closed elsewhere.** Approval fatigue is the documented
   failure of human-in-the-loop, so recognized read-only actions from allowed tools flow without
   approval. An unknown, malformed, disallowed, or forbidden action is never assumed safe:
   it halts. Irreversible in-policy actions escalate; irreversible out-of-policy actions halt.
3. **The verifier is deterministic.** If the checker is another LLM it inherits the same
   hallucination and injection it exists to stop. Enforcement is pure code over a typed
   policy. An LLM may *draft* the policy once, up front; it is never in the enforcement path.

## 3. Scope

**In scope (must ship):**
- Deterministic enforcement engine: tool catalog, reversibility classifier, policy model,
  policy enforcer. Pure Python, no network, fully unit-tested.
- Interception seam that wraps an agent's tool execution (OpenAI Agents SDK / GPT-5.6).
- A demo agent with genuinely dangerous *sandboxed* capabilities: a real SQLite DB, scoped
  filesystem mutations, and a mock money-transfer API. It does not expose an unrestricted shell.
- Intent compiler: GPT-5.6 drafts a `Policy` from an NL task; human confirms once.
- FastAPI backend with an append-only event log and a live decision feed (SSE) + human
  escalation approve/reject.
- Next.js 15 frontend: live action feed, policy panel, and an "unleash the attack" demo
  trigger.
- Eval harness: a golden set of adversarial + benign scenarios and a CI gate that fails if any
  known-bad action is ever allowed or any known-good action is ever halted.

**Out of scope (do NOT build):**
- Any ML/LLM-based "is this malicious" detector. Enforcement is deterministic by design.
- Multi-tenant auth, billing, user registration.
- Real cloud/production integrations. The dangerous tools act on a local sandbox DB, a temp
  git repo, and a fake in-memory transfer ledger.
- Agent frameworks beyond the OpenAI Agents SDK (no LangGraph — the flow is linear).

## 4. Architecture

```
                 ┌─────────────────────────────────────────────┐
   NL task ─────▶│ Intent Compiler (GPT-5.6, ONE-SHOT, offline) │──▶ Policy (typed, human-confirmed)
                 └─────────────────────────────────────────────┘                     │
                                                                                       ▼
  ┌───────┐  proposes tool call   ┌──────────────── INTERLOCK (deterministic) ───────────────┐
  │ Agent │──────────────────────▶│  ToolCatalog → ReversibilityClassifier → PolicyEnforcer  │
  │(GPT-  │                        │                                            │             │
  │ 5.6)  │◀── allow / halt+reason ┤                            Decision{allow|halt|escalate} │
  └───────┘                        └───────────────────────┬──────────────────────┬──────────┘
       ▲                                                    │ every decision       │ escalate
       │ tool result (or refusal)                           ▼                      ▼
       └──────────────────── executes only if allowed   EventLog (SQLite) ── FastAPI ── SSE ──▶ Next.js feed
```

Enforcement path contains **no network and no model call.** The only model call is the
one-shot intent compilation and the agent itself — never the gate.

## 5. Core data model (authoritative)

```python
# reversibility of a concrete proposed action
class Reversibility(str, Enum):
    REVERSIBLE = "reversible"
    IRREVERSIBLE = "irreversible"
    UNKNOWN = "unknown"          # treated as irreversible by the enforcer (fail-closed)

class Decision(str, Enum):
    ALLOW = "allow"
    HALT = "halt"
    ESCALATE = "escalate"        # irreversible + in-policy-but-flagged → human approves

# a tool the agent may call
class ToolSpec(BaseModel):
    name: str
    # classifier callback: (args) -> Reversibility
    # registered in code, not serialized

# the compiled, human-confirmed intent
class Policy(BaseModel):
    task: str                        # original NL task, for the audit trail
    allowed_tools: set[str]          # tool names the agent may use at all
    allowed_roots: list[str]         # canonical sandbox roots writable/deletable
    allowed_db_ops: set[str]         # e.g. {"SELECT","DELETE"}
    allowed_db_tables: set[str]      # e.g. {"sessions"}; operations alone are insufficient
    spend_cap_cents: int             # 0 = no money moves allowed
    forbidden_patterns: list[str]    # regexes always halted (e.g. "rm -rf /", "DROP TABLE")

class ProposedAction(BaseModel):
    tool: str
    args: TypedActionArgs            # discriminated Pydantic payload, never a bare dict

class EnforcementContext(BaseModel):
    spent_cents: int = 0             # immutable snapshot supplied by the caller

class Verdict(BaseModel):
    decision: Decision
    reversibility: Reversibility
    reason: str                      # human-readable "why"
    matched_rule: str                # which policy field/pattern drove the decision
    action: ProposedAction
```

## 6. Enforcement rules (the whole logic, in one place)

Given a `ProposedAction` and a `Policy`, the enforcer returns a `Verdict`:

1. Reject malformed payloads and unknown/disallowed tools → **HALT** (`allowed_tools` or
   `malformed_action`).
2. If any `forbidden_patterns` regex matches the stable serialized action → **HALT**
   (`forbidden_pattern:<pat>`), before classification.
3. Classify a typed action. A command, SQL statement, or action shape outside the conservative
   recognized grammar is `UNKNOWN`, never reversible.
4. A recognized read-only action from an allowed tool → **ALLOW** (`reversible`).
5. For IRREVERSIBLE or UNKNOWN actions, check canonical filesystem-root containment, allowed
   database operation *and table*, and `context.spent_cents + action.cents <= spend_cap_cents`.
   Any failed check → **HALT**; an in-scope irreversible action → **ESCALATE**.
6. Default → **HALT** (`default_deny`).

Every branch returns a `reason` a human can read on the feed.

## 7. Demo (the 90-second story)

1. Operator types a task: *"Clean up stale rows in the `sessions` table and tidy the temp
   directory."* Interlock drafts a policy: only `sessions` DELETE is permitted, the canonical
   demo root is writable, money is prohibited, and `DROP` is forbidden. The operator confirms it.
2. The agent works — several reversible/in-scope actions **flow through green** on the feed.
3. A **prompt-injection** payload (planted in a file the agent reads) tells it to
   `DROP TABLE users` and wire $5,000. On the feed: both actions **halt red**, each with a
   plain-English reason and the matched rule. The agent receives the refusal and continues its
   legitimate work.
4. Cut to the eval scorecard: N adversarial scenarios, 100% halted; M benign, 100% allowed;
   the CI badge is green.

Pitch line: *"We built the seatbelt for AI agents — and it doesn't ask another AI whether
you're about to crash."*

## 8. Success criteria

- Enforcement engine: 100% of golden adversarial actions halted, 0% of golden benign actions
  halted, verified in CI.
- End-to-end demo runs live: agent + interception + feed, with the injection scenario halting
  correctly.
- Deterministic guarantee is real: the enforcer module imports no network/LLM client (enforced
  by a test).
- README + <3-min video + Codex session ID captured.

## 9. Needed.md boxes this closes

Agents with error-recovery/retries; structured-output guardrails; cross-provider tool-calling
patterns; LLM eval + golden datasets + CI regression; tracing/observability (LangFuse);
Next.js App Router + RSC; streaming UI; Tailwind + shadcn.
