# Multica comparison and additive integration boundary

**Status:** research record; no Multica-derived implementation is approved by this document.

## Source-reviewed scope

Multica presents itself as a managed-agent platform: teams assign issues to coding
agents, monitor their lifecycle, route work through squads, run recurring
autopilots, and retain reusable skills.  Its architecture includes a web UI, Go
backend, PostgreSQL/pgvector, and a local daemon that executes supported coding
agent CLIs.  This assessment is based on the project's public README, reviewed
2026-07-18: <https://github.com/multica-ai/multica>.

## Direct comparison

| Concern | Multica | Interlock |
| --- | --- | --- |
| Primary job | Orchestrate and manage a fleet of coding agents | Independently evaluate a proposed agent action/change before release |
| Unit of work | Issue, assignee, squad, agent runtime, task status | Policy/action trace, authority delta, effect contract, replay case, evidence bundle |
| Runtime model | Long-running local/cloud agent execution via a daemon | Deterministic, local-only evaluation; no external effects inside the engine |
| Memory | Reusable team skills | Reviewer-governed incidents and replay fixtures that prevent known failure patterns from recurring |
| Decision | Route and observe work | Produce an auditable allow/block/escalate/advisory decision |

They solve adjacent problems, not the same problem.  Rebuilding Multica's board,
daemon, scheduling, provider adapters, or workspace management would be a
strategic duplication and would weaken Interlock's independent-enforcer role.

## Best additive opportunity: an external assurance gate

Treat a managed-agent platform as an **untrusted execution/orchestration
adapter**, not as a dependency of the deterministic engine:

1. The orchestrator emits a normalized *proposed change* and typed action trace.
2. An Interlock adapter maps it into the existing policy/authority/effect
   contracts.
3. The pure engine evaluates the request and creates an evidence bundle.
4. The orchestrator may continue only for `allow` / explicitly approved
   `escalate` outcomes; its task timeline receives the decision reference.
5. A human-reviewed incident can be promoted to a replay fixture and checked
   against subsequent proposed changes.

This keeps every security-relevant decision reproducible even if an upstream
agent provider, daemon, or workflow product changes.

## Additive roadmap candidates (not yet implemented)

1. **Orchestrator-neutral adapter contract (highest value).** Define a versioned
   `ProposedChangeEnvelope` with task ID, repository revision, typed tool/action
   trace, declared authority, and correlation ID.  Implement a local fixture
   adapter first; do not call a third-party API.
2. **Decision callback schema.** Return only minimum data needed by an
   orchestrator: verdict, reasons, approval requirement, evidence digest, and
   replay-case references.  This preserves privacy and makes the integration
   replaceable.
3. **Task-to-evidence dashboard linkage.** Add a dashboard view that relates a
   task/correlation ID to authority delta, replay trials, reviewer decision, and
   verified bundle.  It is an assurance view, not a competing project board.
4. **Skill admission checks.** If a platform proposes storing a reusable skill,
   evaluate its declared tools, authority, secrets exposure, and regression
   fixtures before admission.  This is the strongest way to make "memory" safe:
   mistakes become controlled test cases, not opaque prompt history.
5. **Portable trace imports.** Add adapters for common audit representations
   (for example OpenTelemetry-like spans) only after the normalized trace
   contract is stable and tested.  Adapters must fail closed on missing required
   semantics.

## Guardrails and non-goals

- No agent daemon, remote login, cloud control plane, credentials, or outbound
  action is introduced by this proposal.
- The current deterministic engine remains the policy decision boundary; adapters
  may translate data but cannot override a verdict.
- Raw prompts, source code, and secrets must not enter privacy-minimized metrics
  or evidence by default.
- Any future provider integration needs separate approval, contract tests,
  failure-mode tests, and a kill switch.

## Decision

Complete the remaining local assurance UI/CLI/recovery work first.  Then propose
the local fixture version of the orchestrator-neutral envelope as the first
Multica-inspired extension.  Do not implement a direct Multica integration until
the user explicitly authorizes an external integration.
