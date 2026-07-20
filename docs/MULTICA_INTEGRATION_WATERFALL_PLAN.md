# Multica integration waterfall plan

**Owner:** Principal Engineering  
**Status:** Planning only — no Multica client, daemon, credentials, network call, or production integration is authorized by this document.  
**Product decision:** Interlock remains the independent, deterministic change-control plane. Multica is treated as an orchestration system and an untrusted source of typed proposed-change data.

## 0. Executive outcome

The integration will let a Multica-managed agent task obtain an Interlock advisory verdict before a change is promoted or a reusable skill is admitted. The integration must answer, reproducibly:

1. Which task, agent, repository revision, and declared authority produced this change?
2. Did the proposed change expand effective authority or protected effects?
3. Did applicable, human-approved incident regressions replay successfully in isolation?
4. Can a reviewer independently verify the result without relying on Multica’s mutable task state?
5. If Interlock is unavailable or input is incomplete, does the orchestrator fail safely into review/quarantine rather than continue silently?

## 1. Scope and non-goals

### In scope

- A versioned `ProposedChangeEnvelope` adapter contract.
- Local fixture adapter first; no live Multica API dependency.
- Normalization from task/run metadata into existing manifest, authority, replay, and evidence contracts.
- Advisory decision callback contract for a task timeline.
- Skill-admission evidence checks.
- Task/run-to-evidence linkage, redaction, audit, recovery, and rollout metrics.

### Explicitly out of scope

- Rebuilding Multica’s board, scheduling, daemon, workspace model, runtime routing, or provider adapters.
- Dispatching tools, modifying a task, approving code, or changing Multica state from Interlock.
- Treating an agent-generated trace as authoritative policy.
- Production credentials, OAuth/OIDC, webhook endpoints, cloud deployment, or a GitHub App without a separate approved production plan.

## 2. Waterfall Phase 1 — Requirements and acceptance baseline

### Functional requirements

| ID | Requirement | Acceptance evidence |
|---|---|---|
| MR-01 | Accept a strict, versioned proposed-change envelope. | Unknown fields and unsupported versions reject deterministically. |
| MR-02 | Bind every result to task/run/correlation identifiers without storing raw prompts by default. | Evidence contains stable identifiers and redaction tests pass. |
| MR-03 | Normalize declared authority into Interlock’s semantic authority surface. | Tool, repo, environment, principal, and budget expansions are detected. |
| MR-04 | Evaluate policy delta, approved replay cases, and effect contracts locally. | Pass/fail/inconclusive cases are reproducible. |
| MR-05 | Return a minimal advisory callback. | Callback contains verdict, reason codes, evidence digest, and review requirement only. |
| MR-06 | Support skill admission as a proposed change class. | Unsafe or incomplete skill admission is inconclusive/fails; no auto-admission. |
| MR-07 | Quarantine incomplete/suspicious inputs. | Missing trace/digest/authority yields review-only outcome. |
| MR-08 | Preserve recovery and audit history. | Export/import and tamper checks remain valid. |

### Non-functional requirements

- **Determinism:** normalized fixture input produces the same verdict and digest on repeated runs.
- **Isolation:** no live network, daemon, shell, or provider operation in local verification.
- **Privacy:** prompts, source contents, tokens, and credentials are excluded from default metrics/evidence.
- **Availability:** Interlock failure maps to `inconclusive / review_required`; it never maps to approval.
- **Compatibility:** existing Interlock demo and `interlock.engine` remain unchanged.
- **Observability:** counters include only fixed outcome labels; correlation IDs remain local evidence fields, not metrics dimensions.

### Requirements exit gate

Product, QA, security, and architecture owners approve an ID-to-test traceability matrix. No implementation begins until every requirement has an owner, negative case, and explicit fallback behavior.

## 3. Waterfall Phase 2 — Architecture and threat model

### Target boundary

```text
Multica task/run/skill event (untrusted metadata)
                 ↓
    Adapter validation + redaction + schema version check
                 ↓
       ProposedChangeEnvelope (immutable local contract)
                 ↓
 Manifest capture → authority delta → replay/effect contracts
                 ↓
       Release evidence bundle + advisory callback
                 ↓
 Multica timeline: continue | reviewer required | quarantine
```

### Architectural rules

1. The adapter may translate inputs but may not override a deterministic Interlock result.
2. Interlock never assumes an external task is authentic solely because it has an ID.
3. Every external integration is behind an interface with a local fixture implementation.
4. Evidence is immutable once created; corrections create a new bundle with provenance.
5. Failures in normalization, verification, or replay produce `inconclusive`, not `pass`.

### Threats and mandatory controls

| Threat | Control | Test |
|---|---|---|
| Forged task/run metadata | Signed/authenticated transport deferred; local adapter labels provenance unverified. | Unverified envelope cannot become blocking approval. |
| Prompt/trace poisoning | Never insert raw trace data into policy or prompt context. | Poisoned trace remains inert candidate data. |
| Hidden authority expansion | Typed authority comparison, not textual diff. | Added repo/tool/environment/budget tests. |
| Unsafe skill propagation | Reviewer-gated skill admission and replay suite. | Unapproved skill cannot become admissible. |
| Adapter outage | Explicit `inconclusive` callback and quarantine. | Fault injection. |
| Evidence tampering | Canonical digest verification and linked identifiers. | Field/reference mutation fails verification. |
| Data overcollection | Allowlisted envelope fields and metrics labels. | Secret/PII rejection/redaction tests. |

### Architecture exit gate

ADR set is approved for envelope versioning, provenance, callback semantics, skill admission, quarantine behavior, storage retention, and future authentication. Threat-model review must identify no path from raw external input to runtime authority.

## 4. Waterfall Phase 3 — Detailed design

### 4.1 ProposedChangeEnvelope v1

Required fields:

- `schema_version`, `correlation_id`, `source_system`, `task_id`, `run_id`
- `change_class`: `code_change | policy_change | skill_admission | adapter_change`
- immutable revision/component digests
- declared principal, runtime/provider label, environment, repository selector
- typed authority declaration and normalized action trace reference
- provenance state: `fixture | externally_verified | unverified`

Rules:

- `extra=forbid`; identifiers are length-bounded and normalized.
- The envelope contains references/digests, not raw prompt/source payloads.
- Missing authority, unknown change class, unsupported version, or ambiguous trace is `inconclusive`.
- Only `fixture` provenance is permitted in the initial local release.

### 4.2 Advisory callback v1

```json
{
  "schema_version": 1,
  "correlation_id": "…",
  "verdict": "pass | fail | inconclusive",
  "action": "continue_advisory | reviewer_required | quarantine",
  "reason_codes": ["authority_expansion"],
  "evidence_digest": "sha256…",
  "replay_case_ids": [12, 19]
}
```

No prompt text, policy body, secret, or agent output may appear in the callback.

### 4.3 Skill admission policy

Skill admission is modeled as a release candidate, never as a learning shortcut:

1. Capture skill identity/version/digests and declared authority.
2. Compare against prior approved version or a zero-authority baseline.
3. Select relevant active regressions; missing required coverage is inconclusive.
4. Run isolated replay/effect checks.
5. Assemble evidence and require reviewer sign-off for expansion/high-risk classes.
6. Retirement/revocation removes admission eligibility without deleting history.

### Detailed-design exit gate

Pydantic schemas, JSON examples, OpenAPI shapes, error taxonomy, and sequence diagrams are reviewed by backend, QA, and security before code begins.

## 5. Waterfall Phase 4 — Build sequence

Every package follows TDD: failing test → minimum implementation → focused tests → full Python/eval/frontend gate → small commit.

### WP-M0: Contract foundations

- Implement envelope and callback schemas plus canonical digest rules.
- Add valid, malformed, forward-version, and redaction fixtures.
- **Done when:** parser and canonicalization tests are deterministic and default-deny.

### WP-M1: Local fixture adapter

- Implement adapter protocol and a fixture-only Multica-shaped adapter.
- Normalize into existing manifests/traces without engine imports.
- **Done when:** mapping is contract-tested for code/policy/skill changes.

### WP-M2: Decision composition

- Compose delta, replay, effect contracts, and evidence into callback semantics.
- Add quarantine/inconclusive paths and reason codes.
- **Done when:** a callback cannot report continue when evidence is incomplete.

### WP-M3: Skill admission workflow

- Add skill-admission capture/review/replay/evidence lifecycle.
- Reuse existing candidate governance and retirement mechanisms.
- **Done when:** unreviewed/expanded/failed skills cannot be marked admissible.

### WP-M4: Developer surfaces

- Add local CLI/API/dashboard fixture views: envelope inspection, decision report, callback preview, evidence verification.
- **Done when:** demo completes envelope → replay → advisory callback → verify without external effect.

### WP-M5: Recovery and observability

- Add aggregate counters for envelope outcome classes and adapter failure modes.
- Include envelope/evidence linkage in export/import; update operations runbook.
- **Done when:** restore drill preserves evidence linkage and metrics contain no sensitive values.

## 6. Waterfall Phase 5 — Integration and verification

### Required test matrix

- Unit: schema, redaction, canonicalization, delta mapping, callback construction.
- Property/fuzz: unknown fields, ordering, malformed identifiers, authority monotonicity.
- Component: SQLite lifecycle, replay selection, evidence chain, recovery import/export.
- Integration: fixture adapter → Interlock API → callback → verifier.
- E2E: dashboard and CLI local demonstrations.
- Security: poisoning, hidden authority, missing provenance, bundle tampering, snapshot conflict, path escape.
- Failure: adapter unavailable, invalid trace, missing digest, replay error, verifier error.
- Performance: baseline latency and repeated-run stability, measured outside engine.
- Accessibility: keyboard-only control operation, labels, focus visibility, live status/error states.

### Golden scenarios

1. Safe code change with no authority delta and passing replay → advisory continue.
2. Added write tool/repository/environment → reviewer required/fail by policy.
3. Skill with no declared authority → quarantine/inconclusive.
4. Skill that fails prior incident replay → fail with case reference.
5. Tampered callback/bundle → verification failure.
6. Adapter timeout/unavailable → inconclusive; existing runtime demo still works.
7. Snapshot restore preserves case-to-task correlation linkage.
8. Raw prompt/secret-like input is rejected/redacted before persistence.

### Verification exit gate

- Full suite, existing evaluation corpus, adapter suite, and frontend build are green.
- Browser workflow proves no live external action is invoked.
- No unsafe-miss or false-block regression in existing controlled corpus.
- QA signs a report with residual risks, skipped tests, and exact environment.

## 7. Waterfall Phase 6 — Release, operations, and production readiness

### Progressive rollout

1. Local fixture-only, report-only.
2. Seeded/staging adapter with signed/authenticated transport after approval.
3. Advisory callback shown on external task timeline.
4. Measured, change-class-specific reviewer-required policy.
5. Only after measured accuracy and security review: optional blocking for narrowly defined changes.

### Feature flags and rollback

- `multica_adapter_enabled`: default false.
- `multica_callback_enabled`: default false.
- `skill_admission_advisory`: default true when adapter enabled.
- `quarantine_on_inconclusive`: default true for high-risk classes.
- One-step rollback disables adapter/callback while preserving evidence locally.

### Production prerequisites (separate approval)

- Authenticated transport and secret management.
- Tenant/workspace isolation and authorization model.
- Rate limits, retries, idempotency keys, webhook signature verification.
- Retention/deletion policy, backups, restore drill, alerting, incident ownership.
- Dependency/license/supply-chain review and load testing.

### Final production exit gate

Architecture, security, QA, operations, and product sign off on threat model, rollback rehearsal, independent evidence verification, privacy review, SLOs, and residual risks. Until then, the integration remains local and advisory.

## 8. Change control

Any request to add a live Multica API call, credential, webhook, daemon control, or production callback is a scope change. It requires an ADR, threat-model update, integration tests, explicit user authorization, and a new release gate.
