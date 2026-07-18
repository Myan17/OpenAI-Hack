# Implementation plan — developer-agent change control

**Status:** approved for planning only. This plan does not alter the running
demo, its API, its pure enforcement engine, or the local workflow.

## What changes and what does not

The current project remains the **reference enforcement adapter**: it takes a
typed action, evaluates it deterministically, and records an effect in a safe
local sandbox. The new product layer is additive: it validates whether a
change to an agent system broadens authority or regresses known effects before
that change is promoted.

```text
existing agent → deterministic engine → sandbox adapter → event/effect
                                  │
                                  ▼
new change-control layer: manifest → replay → authority/effect diff → release verdict
```

Compatibility rules:

1. `interlock.engine` stays pure and its decision API is not renamed or made
   network-dependent.
2. Existing API routes, dashboard demo, simulator, and local SQLite data keep
   working unchanged during every phase.
3. New data is stored in separate tables/modules behind an additive API
   namespace; no destructive migration is permitted.
4. Every new workflow starts in `report` mode. It may block promotion only
   after repeatable regression tests prove its verdict is accurate.
5. The public name stays a code name in source until a new name is chosen; no
   bulk rename or breaking repository move occurs during implementation.

## Outcome

For each developer-agent pull request or release, produce one verifiable,
human-readable answer:

> Did this change add authority, alter a protected effect, or fail a
> human-reviewed regression case?

The first supported scenario is a developer agent that reads a GitHub issue,
inspects a repository, proposes a change, and requests permission for a
consequential action. It is purposely a safe local sandbox scenario.

## Phase 0 — baseline and contracts

**Deliverables**

- Snapshot the current demo’s action traces, policy fixtures, and expected
  effects as the compatibility baseline.
- Define versioned schemas for `ChangeManifest`, `AuthorityDelta`,
  `EffectContract`, `CandidateCase`, `ApprovedCase`, `ReplayRun`, and
  `ReleaseEvidenceBundle`.
- Write explicit canonicalization rules for actions, resources, policy
  versions, and effect-state assertions.
- Record the boundaries between runtime authorization, CI change control, and
  observability.

**QA gate**

- Existing unit, evaluation, and frontend-build commands remain green.
- A baseline trace replays to byte-for-byte equivalent deterministic verdicts.
- Schema validation rejects unknown fields, missing provenance, and
  noncanonical resource selectors.

**Workflow impact:** none; documentation and fixtures only.

## Phase 1 — deterministic release comparison

**Deliverables**

- Extract a Change Manifest from agent configuration, policy bundle, tool
  catalog, adapter version, and identity/delegation configuration.
- Implement Authority Delta: new/removed principals, assets, verbs, budgets,
  and approval requirements—not a raw text diff.
- Implement Effect Contracts against local sandbox state, such as "no branch
  created", "no database mutation", or "approval remains required".
- Generate a Release Evidence Bundle linking input digests, policy versions,
  delta, replay result, and verifier metadata.

**QA gate**

- Property tests prove a narrower policy never appears as an expansion.
- Mutation tests catch a broadened table, repository, filesystem root, or
  action verb.
- Tampering with any evidence input produces an invalid bundle.

**Workflow impact:** report-only CLI/API endpoint; existing runtime decisions
are unchanged.

## Phase 2 — safe failure memory and replay

**Deliverables**

- Capture an observed block, escalation, rollback, or reviewer correction as
  a `CandidateCase` with source and redaction metadata.
- Provide review, approve, reject, expiry, owner, and rollback paths.
- Convert approved cases into isolated replay fixtures with reference outcome
  and effect contracts.
- Add repeat trials and `pass`, `fail`, `inconclusive` verdicts for
  nondeterministic outer-agent paths; deterministic policy checks remain
  binary.

**QA gate**

- Candidate records cannot alter a policy, prompt, or runtime decision.
- A case carrying a secret or PII sample is redacted/rejected before storage.
- Replays cannot touch real network, shell, filesystem outside its fixture, or
  production database.
- Expired/revoked cases cannot block a release without renewed review.

**Workflow impact:** all capture is opt-in; existing learning-guardrail UI can
continue to work until migrated behind this governed workflow.

## Phase 3 — developer workflow and user experience

**Deliverables**

- CLI: `capture`, `case review`, `replay`, `diff`, `verify`, and `report`.
- GitHub Check in advisory mode, with a downloadable evidence artifact.
- Console pages for change summary, authority/effect diff, replay failures,
  candidate review, and evidence verification.
- A polished demo: a benign update passes; a policy broadening or poisoned
  path fails; reviewer correction becomes a future regression case.

**QA gate**

- End-to-end browser test verifies the current live demo still works before
  and after the new change-control screens are enabled.
- GitHub Check does not fail open if evidence/replay is unavailable; it
  returns an explicit inconclusive/advisory status.
- Accessibility, empty states, and error paths are tested.

**Workflow impact:** advisory first. Blocking is feature-flagged and opt-in.

## Phase 4 — interoperability and evidence hardening

**Deliverables**

- Stable trace-normalization interface, with the current engine first and
  OpenTelemetry/MCP/gateway import adapters next.
- Signed release evidence and independent verifier.
- Delegated identity bindings and receipt verification where the adapter
  requires it.

**QA gate**

- Adapter conformance suite applies identical normalized traces to every
  adapter.
- Evidence tampering, replay, stale identity, and key rotation tests pass.
- Performance budget is measured against the existing demo baseline.

**Workflow impact:** adapters are opt-in plugins; no existing route switches
implementation until conformance tests pass.

## Phase 5 — production-readiness and public launch

**Deliverables**

- Versioned evaluation corpus, security/utility methodology, deployment
  guide, runbooks, and residual-risk statement.
- Name selected, availability reviewed, README/demo language updated in one
  deliberate compatibility release.
- Optional enforcement mode enabled only after advisory data establishes
  acceptable false-block and unsafe-miss rates.

**QA gate**

- Reproducible clean install and full demo test.
- Release bundle verifier works independently from the server.
- Documentation never claims universal prompt-injection prevention or
  production certification without evidence.

## Phase order and stop conditions

Proceed sequentially. A phase may not start implementation until its schema,
test plan, and rollback path are reviewed. Stop and investigate if any phase
breaks the existing evaluation suite, changes a deterministic engine verdict,
or requires a destructive migration.

## Decisions needed from you

1. Approve this product boundary: **developer-agent change control** rather
   than a general MCP security gateway.
2. Choose a new public product name before Phase 5 branding work.
3. Confirm that GitHub is the first external integration; until then all
   effects remain local test doubles.
