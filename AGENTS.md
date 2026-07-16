# AGENTS.md — Interlock

This file is the single source of truth for any coding agent (Codex/GPT-5.6) working in this
repo. Read it fully before your first action in a session. **Before writing any line of code,
also read `rules.md`** — it lists the non-negotiable constraints.

---

## 1. What you are building

**Interlock** is a runtime **circuit breaker for autonomous AI agents**. It sits between an
agent and its tools and **halts irreversible, out-of-intent actions** while letting benign work
flow through untouched. The gate that makes the decision is **deterministic policy-as-code — it
is never an LLM.**

**One-line pitch:** the seatbelt for AI agents — and it doesn't ask another AI whether you're
about to crash.

**Hackathon:** OpenAI Build Week, **Developer Tools** track. Solo, ~6 days, deadline
2026-07-21 17:00 PT. Judged on: thorough/skillful use of Codex; a coherent runnable product; a
credible specific real problem; novelty.

## 2. Why it matters (say this in the video/README)

Agents already take irreversible actions and get them wrong: a Replit agent deleted a
production database after being told not to; a Cursor agent ran `rm -rf` right after "DO NOT RUN
ANYTHING"; EchoLeak (CVE-2025-32711) made Copilot exfiltrate files from one email. Gartner:
**trust, not capability, blocks deployment**, and through 2028 **≥80% of unauthorized agent
actions are the agent's own misbehavior, not attackers.** So the problem is *intent
reconciliation*, not malware detection.

## 3. The thesis — three claims you must never violate

1. **Intent, not content.** We check "does this action match what the human asked for," against
   a machine-checkable policy — not "is this text malicious."
2. **Gate only irreversible + out-of-intent.** Reversible actions always flow (approval fatigue
   is the documented failure mode). We halt only actions that are *both* irreversible *and*
   outside the compiled intent.
3. **The verifier is deterministic.** An LLM may *draft* a policy once, offline. It is **never**
   in the enforcement path. If you find yourself calling a model to decide allow/halt, stop —
   you are breaking the core idea.

## 4. Architecture (how the pieces fit)

```
NL task ─▶ Intent Compiler (GPT-5.6, ONE-SHOT, offline) ─▶ Policy (typed, human-confirmed)
                                                                     │
 Agent ── proposes tool call ─▶ INTERLOCK ENGINE (pure, deterministic)
 (GPT-5.6)                       ToolCatalog → ReversibilityClassifier → PolicyEnforcer
     ▲                                              │ Verdict{allow|halt|escalate}
     │ allow → run real tool                        ▼
     │ halt  → refusal string           EventLog(SQLite) ─ FastAPI ─ SSE ─▶ Next.js live feed
```

The **enforcement path touches no network and no model.** The only model calls in the whole
system are (a) the one-shot intent compilation and (b) the demo agent itself.

## 5. Repository layout

```
interlock/
  engine/            # PURE, DETERMINISTIC, NETWORK-FREE. The defensible core.
    models.py        #   Reversibility, Decision, Policy, ProposedAction, Verdict
    catalog.py       #   classify(tool, args) -> Reversibility
    sqlkw.py         #   leading_keyword(sql) -> str  (shared by catalog + scope)
    patterns.py      #   matches_forbidden(action, patterns) -> str | None
    scope.py         #   path_in_scope / db_op_allowed / within_spend
    enforcer.py      #   enforce(action, policy) -> Verdict   ← the whole decision
  tools/sandbox.py   # the DANGEROUS surface: run_bash/run_db/transfer/fs_write (real local effects)
  interceptor.py     # guarded_call(action, policy, sink): enforce → dispatch-or-block
  agent.py           # OpenAI Agents SDK wiring (GPT-5.6), tools wrapped by guarded_call
  intent.py          # compile_policy(task) -> Policy  (GPT-5.6 structured output, failsafe)
  api/
    eventlog.py      # append-only EventLog (SQLite), implements EventSink
    main.py          # FastAPI: /policy /run /events /stream /escalation
web/                 # Next.js 15 App Router + TS + Tailwind + shadcn/ui (live feed, policy, controls)
eval/
  scenarios.yaml     # golden adversarial + benign actions
  run.py             # run_eval() -> scorecard; CI fails if any known-bad allowed
tests/               # pytest mirrors the package tree; TDD — test first, always
.github/workflows/ci.yml
docs/superpowers/{specs,plans}/   # the design spec and the implementation plan — read these
```

## 6. Core contracts (do not drift from these names/types)

```python
class Reversibility(str, Enum): REVERSIBLE="reversible"; IRREVERSIBLE="irreversible"; UNKNOWN="unknown"
class Decision(str, Enum):      ALLOW="allow"; HALT="halt"; ESCALATE="escalate"

class Policy(BaseModel):
    task: str
    allowed_tools: set[str]
    allowed_paths: list[str]          # fnmatch globs
    allowed_db_ops: set[str]          # e.g. {"SELECT","INSERT"}; DROP/DELETE absent by default
    spend_cap_cents: int              # 0 = no money moves
    forbidden_patterns: list[str]     # regexes ALWAYS halted

class ProposedAction(BaseModel): tool: str; args: dict
class Verdict(BaseModel): decision: Decision; reversibility: Reversibility; reason: str; matched_rule: str; action: ProposedAction

def classify(tool: str, args: dict) -> Reversibility: ...
def enforce(action: ProposedAction, policy: Policy) -> Verdict: ...
def guarded_call(action: ProposedAction, policy: Policy, sink: "EventSink") -> dict: ...
def compile_policy(task: str) -> Policy: ...
```

## 7. The enforcement algorithm (implement `enforce` exactly in this order)

1. tool not in `policy.allowed_tools` → **HALT** (`matched_rule="allowed_tools"`)
2. any `forbidden_patterns` regex matches → **HALT** (`matched_rule="forbidden_pattern:<pat>"`) — before reversibility
3. `rev = classify(tool, args)`
4. `rev == REVERSIBLE` → **ALLOW** (`matched_rule="reversible"`)
5. irreversible/unknown → scope checks: out-of-scope path → HALT `allowed_paths`; db op not allowed → HALT `allowed_db_ops`; over spend cap → HALT `spend_cap`; else irreversible-but-in-scope → **ESCALATE** (`matched_rule="irreversible_in_scope"`)
6. anything unmatched → **HALT** (`matched_rule="default_deny"`) — **fail closed**

Every branch sets a human-readable `reason`. `UNKNOWN` reversibility is treated as irreversible.

## 8. How to work here

- **TDD, always.** Write the failing test, watch it fail, implement the minimum, watch it pass,
  commit. The plan (`docs/superpowers/plans/2026-07-16-interlock.md`) gives the exact tests.
- **Follow the plan task order.** Phase A (the pure engine) must be complete and green before
  any agent/network/UI work. The engine is the thing that must be perfect.
- **Small, focused files, one responsibility each.** If a file grows past ~150 lines, it's
  probably doing too much.
- **Commit after every green step** with conventional-commit messages (`feat(engine): ...`).
- **Type hints on every function. Pydantic v2 at every boundary.**

## 9. Commands

```bash
# setup
python3.13 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
cp .env.example .env            # then fill keys (never commit .env)

# test (do this constantly)
pytest -q                       # all tests
pytest tests/engine -q          # just the pure engine

# eval gate (must pass; CI enforces it)
python -m eval.run

# run locally
uvicorn interlock.api.main:app --reload      # backend
cd web && npm run dev                         # frontend
bash scripts/seed_demo.sh                     # rebuild sandbox before a demo
```

## 10. Definition of done

- `pytest -q` green; `python -m eval.run` reports `pass: True` (0 known-bad allowed, 0
  known-good blocked); `tests/engine/test_purity.py` green (engine imports no network client).
- Live demo runs end-to-end: agent + interception + feed, with the injection scenario halting
  the `DROP TABLE` and over-cap transfer while benign actions flow.
- README, `docs/DEMO.md`, <3-min video, and the Codex Session ID are captured.

## 11. When unsure

Re-read the three claims in §3. If a change would put a model in the enforcement path, weaken
fail-closed behavior, or gate reversible actions, it is wrong by construction — do not do it.
For anything genuinely ambiguous, leave a `# NOTE(interlock): <question>` and keep the failing
test rather than guessing.
