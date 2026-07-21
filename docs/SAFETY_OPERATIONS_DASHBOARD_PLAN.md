# Safety Operations Dashboard delivery plan

## Product decision

Interlock's web interface is an operator console, not a marketing page. It must answer, from real local state: **what is executing, what was stopped, what requires a reviewer, and what evidence supports the current safety posture.**

The dashboard does not invent tenants, users, policy versions, risk scores, timestamps, model confidence, or cloud deployment state. Missing data is rendered as unavailable or empty. The local demo boundary remains visible on every overview surface.

## Existing data contract

| Surface | Source | Dashboard use | Prohibited claim |
| --- | --- | --- | --- |
| Runtime health | `GET /health` | Local runtime readiness | Production uptime or SLO |
| Decision stream | `GET /events`, SSE `/stream` | Decision counts, filtered event feed, escalation queue | External tool execution history |
| Runs | `GET /runs` | Local run status and detail | Agent ownership or cloud scheduling |
| Guardrails | `GET /guardrails` | Human-review queue | Automatic self-learning enforcement |
| Assurance cases | `GET /assurance/candidates` | Regression review queue | Direct policy mutation |
| Assurance health/metrics | `GET /assurance/health`, `GET /assurance/metrics` | Advisory/evidence posture | Production release certification |
| Evidence bundle | Existing fixture actions | Digest, authority delta, replay outcome | Real Multica callback or deployed release proof |

## Information architecture

```text
Overview
  ├─ Safety posture cards
  ├─ Recent decision breakdown
  ├─ Review queue
  └─ Evidence posture
Live activity
  ├─ Verdict feed
  └─ Local run history
Policy studio
  ├─ Task and generated policy
  ├─ Explicit confirmation
  └─ Simulator / guarded demo
Assurance
  ├─ Guardrails and regression cases
  └─ Evidence bundle and fixture adapter preview
```

## Delivery sequence and quality gates

1. **Overview:** live verdict/run/assurance aggregation, explicit local-data boundary, contract test, frontend build.
2. **Review and activity:** a dedicated queue for pending escalations, guardrails, and assurance cases; actionable navigation and filtering; browser interaction test.
3. **Policy and evidence:** policy authority summary/diff and evidence posture panels without giving evidence any runtime authority; Python contract tests and frontend build.
4. **Repository experience:** authentic screenshots, README walkthrough, capability boundary, and comparison positioning.
5. **Release gate:** responsive browser review; full `pytest`; golden evaluation; frontend build; clean commit and push.

## UX acceptance criteria

- The initial view exposes only data sourced from existing API state.
- A reviewer can see every pending approval in one place and jump to its control.
- The primary policy flow remains functional and keyboard accessible.
- Verdict color is redundant with a textual label and semantic detail.
- On mobile, overview cards and navigation collapse without hiding core actions.
- Every data boundary is explicit: local fixture, report-only, advisory, or unavailable.
