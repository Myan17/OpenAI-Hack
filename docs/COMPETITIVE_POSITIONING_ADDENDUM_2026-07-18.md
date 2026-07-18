# Competitive-positioning addendum — 18 July 2026

## Status

This addendum supersedes the **public positioning** and expansion order in
`DEEP_RESEARCH_MEMO_2026-07-18.md`. It does not invalidate the existing
deterministic evaluator or its safety invariants.

## Material findings

### 1. The name is already in active use for an adjacent product

An active product named [Interlock](https://getinterlock.dev/) positions
itself as a runtime MCP trust layer that detects effective-permission drift,
quarantines tools, and emits hash-chained security receipts. Its source
repository describes the same category. This is enough of a practical naming
and discoverability collision that this project should **not** use
"Interlock" publicly without a new name and a proper legal clearance.

This is a product recommendation, not a trademark opinion.

### 2. "Behavioral contracts for agents" is also a populated category

Public projects and research already offer contract DSLs, trace validators,
runtime enforcement, and CI gates. Examples include
[AgentAssert](https://agentassert.com/),
[agentic-behavioral-contracts](https://pypi.org/project/agentic-behavioral-contracts/),
and [AgentAssay](https://arxiv.org/abs/2603.02601). A product described only
as "pytest for agent behavior" or "agent behavioral contracts" would be
easy to dismiss as a clone.

### 3. The unoccupied, demonstrable wedge is change-control evidence

The project should focus on a question ordinary gateways, policy engines, and
eval runners do not answer together:

> When a developer-agent system changes, what concrete capabilities,
> authority boundaries, and externally visible effects changed—and which
> human-reviewed incidents prove the release is safe to promote?

This is **Developer-Agent Change Control**: a CI-native, gateway-independent
release gate for an agent *system* (agent configuration, model, tools,
adapters, permissions, and policies), not a replacement for runtime access
control or generic quality evaluation.

## Revised product contract

### Product boundary

The product consumes traces and change manifests from the existing evaluator,
SDKs, MCP gateways, or observability systems. It builds a versioned **behavior
change set** for each pull request or release:

1. identify changed model/prompt/tool/policy/adapter/identity inputs;
2. replay a curated, sanitized failure corpus in an isolated environment;
3. compare requested authority, attempted actions, and verified effects with
   the approved baseline;
4. produce an explainable release verdict: `promote`, `needs review`, or
   `block`;
5. attach evidence and the exact regression cases to the pull request;
6. turn an approved incident correction into a new regression fixture.

The existing evaluator remains a high-value **reference adapter** and safe
demo surface. It is not the whole product.

### Distinctive primitives

- **Change Manifest** — a signed diff of agent configuration, model/provider,
  tool schema/version, identity grants, adapter release, and policy bundle.
- **Authority Delta** — a semantic comparison of what principals and agents
  can attempt before and after the change; it is more useful than a text or
  YAML diff.
- **Effect Contract** — an assertion over sandboxed external state (for
  example, branch protection unchanged, database write absent, deployment
  not created), not merely over an agent’s final prose.
- **Incident-to-Regression Workflow** — a candidate case is redacted,
  canonicalized, replayed, and reviewer-approved before it can gate any
  release. It is never pasted into an agent prompt or allowed to mutate policy
  automatically.
- **Release Evidence Bundle** — replay result, authority delta, effect
  verification, human approvals, policy/case versions, and receipt hashes as a
  portable pull-request artifact.

## Security requirements for the requested learning memory

Persistent free-form memory is an unsafe product primitive. Recent work shows
that data written through normal interactions can later steer a consequential
action, including through multi-step or trigger-conditioned poisoning
([MemPoison](https://arxiv.org/abs/2607.14651)).

The failure corpus therefore has these non-negotiable rules:

- untrusted observations are `candidate` records, never authority;
- source, actor, tenant, redaction state, and retention owner are immutable;
- payloads are minimized and secrets/PII are removed before review;
- promotion requires a human reviewer and a reference outcome;
- approved cases are versioned fixtures, not model context;
- fixtures have expiry, owner, rollback, and tamper-evident revision history;
- execution uses isolated fixtures and mock/sandbox effect adapters by default.

## Validation methodology

The project must demonstrate more than a polished dashboard. Each release
should report:

- **unsafe misses:** harmful authority/effect change allowed;
- **safe-work blocks:** legitimate change incorrectly blocked;
- **effect-verification rate:** verdicts corroborated by sandbox state;
- **replay coverage:** weighted percentage of approved failure cases run;
- **regression consistency:** repeated-trial pass rate for nondeterministic
  paths, with `inconclusive` rather than a false pass;
- **review burden:** median decision time and reviewer overrides;
- **evidence completeness:** trace, action, authority, policy, and effect
  linkage present and independently verifiable.

This follows practical agent-evaluation guidance: use deterministic graders
for action/effect facts, model-based graders only where nuance requires them,
and human calibration for the latter. It also avoids the common failure mode
of judging only a plausible final answer while ignoring the tools and state
that produced it. See [Anthropic’s agent-evals guidance](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents/).

## Revised build plan — no product expansion yet

### Phase A — decision and definition

1. Select a new public product name after availability and legal review.
2. Freeze a one-sentence promise: *prove an agent release did not expand
   authority or regress known effects before promotion.*
3. Write schemas for Change Manifest, Authority Delta, Effect Contract,
   Candidate Case, Approved Case, and Release Evidence Bundle.
4. Define the initial GitHub developer-agent scenario and its negative cases.

### Phase B — core assurance loop

1. Add a change-manifest extractor for the existing agent/policy demo.
2. Implement deterministic authority-delta and effect-contract comparison.
3. Build candidate-case review, redaction, approval, expiry, and rollback.
4. Build isolated replay with repeat trials and three-state verdicts.
5. Emit a signed, exportable release evidence bundle.

### Phase C — developer workflow

1. Add CLI commands: `capture`, `case review`, `replay`, `diff`, `verify`,
   and `report`.
2. Add a GitHub Check that blocks a pull request only on a material,
   reproducible safety regression.
3. Add a console view that explains the changed authority/effect in human
   language and links it to the exact approved cases.

### Phase D — runtime and interoperability

1. Keep the existing deterministic engine as a reference enforcement adapter.
2. Add OpenTelemetry trace import and an MCP/gateway adapter behind a stable
   normalization interface.
3. Add signed identity/delegation and receipt verification only after the
   change-control loop is proven end to end.

## What not to build as the headline

- another general MCP proxy or tool scanner;
- an autonomous memory that learns and deploys its own guardrails;
- a broad "agent governance platform" claim;
- a single-run, output-only evaluation dashboard;
- a guarantee of universal prompt-injection prevention.

## Decision required before implementation resumes

Choose the new public identity and approve this narrower product scope. Until
then, retain the code name only internally and preserve the current working
demo without expanding it under a collision-prone brand.
