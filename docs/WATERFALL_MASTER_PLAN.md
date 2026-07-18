# Waterfall master plan — Developer-Agent Change Control

**Document owner:** Principal Engineering

**Lifecycle:** Requirements → System Design → Detailed Design → Build →
Integration → Verification → Release → Operations

**Planning status:** Baseline for implementation. No product code changes are
authorized by this document alone.

**Scope status:** The existing Interlock demo remains the protected reference
enforcement adapter. A public product rename is intentionally deferred until
name availability and legal review are complete.

---

## 1. Executive decision

The product will become a **developer-agent change-control system**. It does
not compete as a generic MCP gateway, prompt filter, or generic “agent
behavioral contract” library. It controls promotion of *changes* to an agent
system by proving whether a proposed release expands authority, changes a
protected effect, or regresses a human-reviewed historical failure.

The runtime engine continues to make only deterministic `allow`, `halt`, or
`escalate` decisions. The new layer must not make the engine intelligent,
networked, probabilistic, or self-modifying.

### 1.1 Product promise

For an agent change set, the system produces a release-evidence bundle that
answers these questions before promotion:

1. What changed: model/prompt/configuration, policy, tool, adapter, identity,
   or deployment metadata?
2. Did the change expand any effective authority or bypass an approval?
3. Does it preserve expected external effects in an isolated sandbox?
4. Does it replay all applicable, human-approved failure cases successfully?
5. Is the decision evidence complete enough for a reviewer to reproduce it?

### 1.2 Non-goals

- Preventing every prompt injection or proving semantic task usefulness.
- Replacing IAM, an MCP gateway, observability, an agent framework, or SAST.
- Giving a model permission to approve, alter policy, or write guardrails.
- Running real GitHub, cloud, database, shell, or payment effects in the
  hackathon demo.
- Rebranding or bulk-renaming the repository before the name decision.

---

## 2. Baseline and inviolable constraints

### 2.1 Protected current behavior

The following is the compatibility baseline and must remain true in every
build:

- `interlock.engine` stays pure Python plus Pydantic: no model, HTTP, network,
  clock, random source, or side effect.
- Unknown, malformed, unrecognized, out-of-scope, or forbidden actions halt.
- Authorized recognized reads remain approval-free.
- In-scope irreversible actions escalate; out-of-scope irreversible actions
  halt.
- Existing FastAPI routes, SQLite event log, SSE feed, Next.js demo,
  simulator, agent flow, and local sandbox behavior continue to work.
- Existing tests and evaluation remain the release floor: no known-bad action
  may be allowed; no known-good action may be blocked.

### 2.2 Compatibility policy

| Area | Policy | Enforcement |
| --- | --- | --- |
| Engine API | No incompatible rename or semantic change without a separate ADR and full regression approval. | Existing engine tests + golden eval. |
| Data | Additive tables and migrations only. No table rewrite/drop in an early phase. | Migration test from a populated SQLite fixture. |
| API | New functionality is under `/assurance/*`; existing routes retain their response shape. | OpenAPI contract snapshot tests. |
| UI | Existing demo route/control flow remains the default experience. | Browser smoke test before/after feature flag. |
| Enforcement | New assurance verdicts start advisory. Runtime policy is not altered by a candidate case. | Explicit feature flag defaults to off. |
| Effects | All development/replay effects are fixture-local and deterministic. | Sandbox escape and no-network tests. |

### 2.3 Production engineering principles

1. **Fail safe, explain clearly.** Unknown evidence causes `inconclusive` or
   `needs review`, never a fabricated pass.
2. **Evidence before automation.** A release can be blocked only by a stable,
   reviewable, reproducible reason.
3. **Least authority.** Every integration and test fixture receives only the
   capability it needs.
4. **Secure learning boundary.** Observations are data. Only approved,
   redacted, versioned fixtures affect a release gate.
5. **Progressive delivery.** Every new function starts report-only, then
   advisory, then optionally blocking after measured accuracy.
6. **Operational reversibility.** All rollout paths have feature flags,
   migration rollback, known owners, and explicit recovery actions.

---

## 3. Waterfall Phase 1 — Requirements baseline

### 3.1 Functional requirements

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| FR-01 | Capture a versioned change manifest for policy, agent config, tool catalog, adapter release, and identity configuration. | A canonical manifest validates; its digest is stable for identical input. |
| FR-02 | Compute semantic authority deltas rather than raw-file diffs. | Broadening a verb, resource, budget, principal, or approval rule is identified with before/after evidence. |
| FR-03 | Define effect contracts over safe sandbox state. | A contract distinguishes “agent said done” from an actual sandbox state change. |
| FR-04 | Capture events as non-authoritative candidate cases. | A candidate cannot change runtime policy or appear in a prompt. |
| FR-05 | Support review, approval, rejection, expiry, ownership, and retirement of candidate cases. | Only a reviewed, active case enters an assurance suite. |
| FR-06 | Replay approved cases in isolation. | Replays are deterministic for engine paths and cannot reach external effects. |
| FR-07 | Return `pass`, `fail`, or `inconclusive` release verdicts. | Missing evidence/replay error yields `inconclusive`, not `pass`. |
| FR-08 | Produce a portable evidence bundle and standalone verification command. | Altering a bundle field or referenced digest makes verification fail. |
| FR-09 | Expose advisory results through CLI, API, dashboard, and a GitHub-ready check abstraction. | Current demo remains usable with assurance disabled. |

### 3.2 Non-functional requirements

| ID | Requirement | Initial target | Test evidence |
| --- | --- | --- | --- |
| NFR-01 | Determinism | Same normalized engine fixture always has same verdict/digest. | 100 repeated-run assertions. |
| NFR-02 | Isolation | No replay leaves its temporary fixture boundary. | Network denied + path escape tests. |
| NFR-03 | Integrity | Release evidence is tamper-evident. | Field, ordering, and reference mutation tests. |
| NFR-04 | Availability behavior | Unavailable evaluator is visible, not silently permissive. | Fault injection produces `inconclusive`. |
| NFR-05 | Performance | Local report-only comparison does not visibly degrade the existing demo. | Baseline versus assurance timing record. |
| NFR-06 | Privacy | Candidate data is minimized and redacted before approval. | Secret/PII fixtures rejected or redacted. |
| NFR-07 | Explainability | Every fail/review verdict identifies manifest field, case, contract, and evidence. | UI/API snapshot review. |
| NFR-08 | Accessibility | New console flows are keyboard operable with meaningful empty/error states. | Automated a11y checks + manual pass. |

### 3.3 Stakeholder and acceptance roles

| Role | Decision rights | Required evidence |
| --- | --- | --- |
| Product owner | Scope, first integration, public name. | Requirements traceability. |
| Principal engineer | Architecture, production gates, exceptions. | ADRs, threat model, design review. |
| Security reviewer | Memory, evidence, identity, release-block criteria. | Abuse cases and negative tests. |
| QA owner | Test completeness and regression release sign-off. | Test report, eval result, replay report. |
| Operator/reviewer | Approves a case or releases a change. | Plain-language evidence bundle. |

### 3.4 Requirements exit gate

Phase 1 is complete only when every requirement has an identifier, owner,
acceptance criterion, test type, and explicit non-goal. Any ambiguous
requirement becomes a recorded decision rather than hidden implementation
behavior.

---

## 4. Waterfall Phase 2 — System architecture and threat design

### 4.1 Target architecture

```text
                         Change-control plane (additive)
 ┌───────────────────────────────────────────────────────────────────┐
 │ Manifest capture → Canonicalizer → Authority/effect comparator      │
 │        │                       │                                    │
 │        ▼                       ▼                                    │
 │ Candidate-case workflow → Approved assurance suite → Replay runner  │
 │                                      │                               │
 │                                      ▼                               │
 │                         Release evidence bundle + verifier           │
 └───────────────────────────────────────────────────────────────────┘
                ▲                           │ advisory result
                │ normalized trace/effect    ▼
 Existing agent → deterministic engine → local sandbox → existing event/API/UI
```

### 4.2 Component boundaries

| Component | Responsibility | Must not do |
| --- | --- | --- |
| Manifest service | Canonicalize versioned release inputs. | Read arbitrary repository secrets or create authority. |
| Authority-delta service | Compare effective permits/constraints. | Invoke a model or execute actions. |
| Effect-contract service | Evaluate sandbox state assertions. | Trust agent prose as effect evidence. |
| Case service | Store/review/redact lifecycle data. | Feed raw candidates into the model or engine. |
| Replay runner | Execute fixtures under isolated test doubles. | Use production integrations or general shell access. |
| Evidence service | Link/digest/sign/export decision evidence. | Mutate historical receipts. |
| Assurance API/UI | Present explanatory report/advisory control. | Replace existing enforcement endpoints. |
| Existing engine | Deterministic action enforcement. | Depend on any assurance-plane service. |

### 4.3 Architecture decisions required before build

Each decision must be recorded as an ADR before the corresponding package is
created.

1. **Canonical serialization:** stable JSON representation, explicit field
   ordering, versioned schema, SHA-256 digest format.
2. **Storage:** extend existing SQLite with additive migration-managed tables;
   no second database in the hackathon profile.
3. **Evidence signing:** begin with digest chain and verification interface;
   add external key management only when deployment scope supports it.
4. **Replay isolation:** dependency-injected local test doubles; no real
   network and no generic shell.
5. **Identity:** represent principals/actors as typed metadata now; defer
   production OIDC integration behind an interface.
6. **Integration abstraction:** model GitHub Check as a local adapter contract
   first; do not require live GitHub credentials for core QA.
7. **Feature flagging:** assurance policy is report-only by default and cannot
   influence `interlock.engine` unless deliberately enabled in a later
   release.

### 4.4 Threat model and controls

| Threat | Preventive control | Detection/recovery |
| --- | --- | --- |
| Prompt/case poisoning | Candidates never become prompt context or policy. | Reviewer audit, source provenance, rejection/retirement. |
| Secret retention | Redaction/minimization before persistence. | Secret scan, quarantine, delete-by-retention process. |
| Replay escape | Typed local adapters, allowlisted paths, denied network. | Test isolation report and emergency replay disable flag. |
| Evidence tampering | Canonical digests, linked evidence IDs, standalone verifier. | Verification failure blocks trust in bundle. |
| False release block | Advisory launch, repeated trials, owner override with audit. | Roll back feature flag; investigate fixture/grader. |
| Unsafe release pass | Required coverage/evidence completeness checks. | Incident → candidate case → review → replay regression. |
| Compatibility regression | Additive APIs/data and baseline contract tests. | Immediate flag rollback; preserve old path. |
| Privilege expansion hidden in text | Semantic authority-delta comparison. | Delta report references exact changed permission. |

### 4.5 Architecture exit gate

- Principal review approves component boundaries and ADRs.
- Security review confirms no candidate-to-authority path exists.
- QA review confirms every threat has a test or accepted residual risk.
- A paper trace demonstrates the full benign, unsafe-expansion, and
  inconclusive paths.

---

## 5. Waterfall Phase 3 — Detailed design specifications

### 5.1 Core schemas

All schemas are Pydantic v2, versioned, typed, default-deny, and reject
unknown fields.

| Schema | Required fields | Invariants |
| --- | --- | --- |
| `ChangeManifest` | schema version, release ID, captured time, component digests, source provenance. | Digest input is canonical and complete. |
| `AuthorityDelta` | baseline/current manifest IDs, added/removed/changed permits, risk classification. | Every delta references a canonical source field. |
| `EffectContract` | action class, fixture ID, expected state predicates, forbidden state predicates. | Never relies on LLM judgement for hard state. |
| `CandidateCase` | source event, actor, provenance, redaction state, owner, status. | Not runnable or authoritative before approval. |
| `ApprovedCase` | candidate ID, reviewer, reference outcome, suite version, expiry. | Approval binds to redacted candidate digest. |
| `ReplayRun` | suite/case IDs, environment hash, trial count, per-trial evidence. | Isolated; cannot omit a failed required case. |
| `ReleaseEvidenceBundle` | manifest, delta, replay, contracts, verdict, digests. | Fails verification if a link or digest is inconsistent. |

### 5.2 State machines

**Candidate case lifecycle**

```text
observed → candidate → redacted → under_review → approved → active
                                         │             │         │
                                         └→ rejected   │         ├→ expired
                                                       └→ retired└→ revoked
```

Only `active` cases are eligible for a release suite. `candidate`, `rejected`,
`expired`, `retired`, and `revoked` cases never affect an agent or a release
verdict.

**Release verdict lifecycle**

```text
capture → validate → compare → replay → assemble evidence → advisory verdict
             │            │         │             │
             └────────────┴─────────┴─────────────┴→ inconclusive

advisory pass → optional reviewer approval → promoted
advisory fail → remediation / explicit audited override → re-run
```

### 5.3 Decision rules

| Condition | Verdict | Required explanation |
| --- | --- | --- |
| Required manifest data missing or invalid | `inconclusive` | Missing field and collection owner. |
| Authority expansion hits protected boundary | `fail` | Principal/action/resource before and after. |
| Required effect contract violated | `fail` | Expected/observed sandbox state. |
| Required active replay case fails | `fail` | Case ID, trial, and evidence link. |
| Nondeterministic score lacks sufficient confidence | `inconclusive` | Trial count and confidence rationale. |
| All required checks pass and evidence verifies | `pass` | Coverage and manifest/evidence digests. |

### 5.4 API and CLI contract

New API namespace only:

| Operation | API/CLI | Behavior |
| --- | --- | --- |
| Capture | `POST /assurance/manifests` / `assurance capture` | Validate/canonicalize; no effects. |
| Compare | `POST /assurance/diffs` / `assurance diff` | Return authority/effect delta. |
| Case creation | `POST /assurance/candidates` / `assurance case create` | Store non-authoritative candidate. |
| Case review | `POST /assurance/candidates/{id}/review` / `assurance case review` | Approve/reject with reviewer identity. |
| Replay | `POST /assurance/replays` / `assurance replay` | Run isolated suite. |
| Report | `POST /assurance/reports` / `assurance report` | Assemble advisory verdict. |
| Verify | local-only verifier / `assurance verify` | Verify exported bundle without server trust. |

API error behavior uses typed errors. A verification error must not be converted
into a passing response.

### 5.5 Detailed-design exit gate

- Schema test vectors cover valid, malformed, stale, tampered, and
  forward-version inputs.
- OpenAPI/CLI help text is reviewed for unambiguous human actions.
- Test design maps every requirement and threat to one or more named tests.
- UX wireframes confirm users can identify why a verdict occurred without
  reading raw logs.

---

## 6. Waterfall Phase 4 — Build work packages

Build in this exact order. Every package follows TDD: failing test, minimum
implementation, green targeted tests, full regression gate, small commit.

### WP-0: Baseline harness

- Create immutable baseline fixtures from the current simulator/eval.
- Add current API/OpenAPI and UI smoke snapshots.
- Add a baseline timing record.

**Completion:** current suite, evaluation, and demo smoke all green; fixtures
have owner and digest.

### WP-1: Domain models and canonicalization

- Implement the seven schemas and canonical JSON/digest helpers outside
  `interlock.engine`.
- Add strict parser and version compatibility policy.
- Add test factories with safe fixture-only data.

**Completion:** valid input canonicalizes identically; invalid/unknown input is
rejected; no engine imports changed.

### WP-2: Manifest capture and authority delta

- Create typed manifest capture from the current policy/tool/adapter fixtures.
- Implement permit comparison including verb, resource, budget, principal,
  environment, and approval changes.
- Produce human-readable delta explanations from typed facts only.

**Completion:** expansion, narrowing, equivalent-reformat, and ambiguous input
are all covered with deterministic tests.

### WP-3: Effect contracts and local replay environment

- Define state predicates for the existing sandbox database, workspace, and
  mock ledger.
- Build fixture reset and isolated replay runner.
- Ensure each trial starts clean and records environment fingerprint.

**Completion:** no state leaks across trials; forbidden effects and local path
escapes are detected.

### WP-4: Candidate-case governance

- Implement additive SQLite storage/migration, lifecycle transition rules,
  redaction hooks, owner/expiry, and audit events.
- Implement approval/rejection/retirement APIs and console views.

**Completion:** state transitions are exhaustive; an unapproved candidate
cannot enter a suite or affect runtime enforcement.

### WP-5: Assurance suite, verdict, and evidence bundle

- Select active cases, execute replay, aggregate repeated trials, and apply
  verdict decision rules.
- Assemble/verify linked release evidence bundle.
- Implement report-only feature flag.

**Completion:** pass/fail/inconclusive paths are reproducible; tampering
invalidates evidence; runtime engine path is unchanged.

### WP-6: Developer surfaces

- Add CLI, assurance API, GitHub Check adapter abstraction, and dashboard
  pages.
- Keep GitHub integration local/fake unless credentials and security review
  explicitly authorize a non-production installation.

**Completion:** user can complete capture → review → replay → report → verify
in the demo with no external effect.

### WP-7: Observability, hardening, and release controls

- Add privacy-minimized audit metrics, feature flags, explicit override logs,
  retention jobs, export/import, and operational health endpoints.
- Add performance, fault injection, and chaos tests.

**Completion:** Operations Readiness Review passes (Section 8).

---

## 7. Waterfall Phase 5 — Integration and verification strategy

### 7.1 Test pyramid

| Layer | Scope | Required examples |
| --- | --- | --- |
| Unit | Canonicalizers, deltas, transitions, predicates, verifier. | Unknown field rejected; narrowing not expansion. |
| Property/fuzz | Parser, canonicalization, delta monotonicity. | Formatting cannot hide authority expansion. |
| Component | SQLite migrations, suite selection, bundle assembly. | Candidate cannot bypass approval. |
| Integration | API + local sandbox + replay runner. | Effect contract catches unauthorized state change. |
| End-to-end | Browser/CLI controlled demo. | Existing agent demo and assurance flow both work. |
| Security | Tampering, poisoning, replay, path escape, privacy. | Raw candidate cannot become policy. |
| Performance | Local report latency and repeated-run stability. | No material demo regression. |
| Recovery | Flag disable, migration restore, evidence verification offline. | Failed rollout returns to baseline workflow. |

### 7.2 Required golden scenarios

1. Benign policy formatting change: no authority delta; pass.
2. Added write verb: authority expansion; fail.
3. Broadened filesystem root/database table/repository selector: fail.
4. Lowered spend cap or removed permission: narrowing; pass with explanation.
5. Missing adapter digest: inconclusive.
6. Candidate includes secret-like text: redacted/rejected before approval.
7. Approved injection regression: agent may read hostile content but cannot gain
   new authority or effect.
8. Expired case: excluded with explicit coverage warning.
9. Altered bundle field: standalone verifier fails.
10. Replay test modifies one fixture then another: clean reset proves no leak.
11. Assurance service unavailable: existing runtime demo still works; release
    report is inconclusive.
12. Existing evaluation corpus: unchanged, green, and reported alongside the
    new suite.

### 7.3 Quality gates

| Gate | Required result | Failure response |
| --- | --- | --- |
| Local commit | Targeted tests, format/type checks, diff check. | Do not commit. |
| PR/CI | Full pytest, existing eval, new assurance suite, frontend build. | Block merge. |
| Staging/demo | E2E workflow and effect isolation verified. | Disable new flag. |
| Production readiness | Security/ops checklist approved. | Remain advisory/local. |
| Blocking rollout | Measured false-block/unsafe-miss targets met. | Stay advisory. |

### 7.4 Release quality metrics

- Unsafe miss rate for controlled expansion scenarios: **0**.
- Known-good existing evaluation false-block rate: **0**.
- Evidence completeness for a passing bundle: **100%** required links.
- Candidate-to-active promotion without reviewer: **0**.
- Replay isolation violations: **0**.
- Existing demo regression: **0** failed baseline scenarios.
- Advisory override rate: measured and reviewed; high rate blocks enforcement
  rollout rather than being normalized.

---

## 8. Waterfall Phase 6 — Deployment, operations, and production safety

### 8.1 Environments

| Environment | Purpose | Allowed effects |
| --- | --- | --- |
| Local dev | TDD and fixture authoring. | Temp sandbox only. |
| CI | Reproducible verification. | Isolated ephemeral fixtures only. |
| Demo/staging | Presentation and E2E smoke. | Seeded local demo only. |
| Production (future) | Controlled customer deployment. | Explicitly scoped adapters after separate authorization. |

No production environment is implied by a successful local demo. Production
deployment requires a subsequent infrastructure/security plan covering identity,
key management, tenant isolation, retention, backups, incident response, and
external integration approvals.

### 8.2 Rollout sequence

1. Ship disabled code behind an assurance feature flag.
2. Enable report-only for seeded/local projects.
3. Compare reports with expected human review decisions.
4. Enable advisory UI/Check; collect false-block and unsafe-miss data.
5. Gate only specifically identified change classes after documented review.
6. Keep a one-click disable path; never let assurance failure disrupt existing
   runtime enforcement.

### 8.3 Rollback plan

| Failure | Immediate action | Data/evidence handling |
| --- | --- | --- |
| New API/UI error | Disable assurance feature flag; retain current demo. | Preserve non-sensitive diagnostic evidence. |
| Faulty migration | Restore prior SQLite backup; run migration rollback test. | Do not delete historical events. |
| False blocking verdict | Revert to advisory, add incident case, re-run suite. | Record override with reviewer and rationale. |
| Evidence verification defect | Mark reports untrusted/inconclusive; do not promote. | Preserve original bundle for forensic comparison. |
| Suspected data leak | Disable capture, quarantine candidate records, rotate secrets if applicable. | Follow incident playbook; no silent deletion. |

### 8.4 Operational readiness review

Before claiming a production-capable release, the Principal Engineer, QA owner,
and security reviewer sign off on:

- Architecture and ADRs complete.
- Threat model and residual risks published.
- Restore drill and feature-flag rollback practiced.
- Verification bundle independently reproducible.
- Metrics, alerts, ownership, and support runbook defined.
- Privacy/retention controls tested.
- Dependency, secret, license, and supply-chain review complete.
- Performance/load target and capacity limits measured.
- No known critical issue in authorization, isolation, evidence integrity, or
  candidate governance.

---

## 9. Documentation deliverables

| Artifact | Owner | Required before |
| --- | --- | --- |
| Requirements traceability matrix | Product + QA | Detailed design exit. |
| ADR set | Principal engineer | Build of each affected package. |
| Schema and canonicalization specification | Backend owner | WP-1 completion. |
| Threat model and abuse-case catalog | Security reviewer | WP-4 completion. |
| Test plan and golden corpus guide | QA owner | WP-3 completion. |
| API/CLI reference | Backend owner | WP-6 completion. |
| Demo runbook | Developer advocate | Demo/staging release. |
| Operator/reviewer runbook | Operations owner | Advisory rollout. |
| Recovery/incident playbook | Security + operations | Production-readiness review. |
| Release notes and residual risk | Principal engineer | Each externally visible release. |

---

## 10. Approval checkpoints and next action

| Checkpoint | Decision needed | Implementation permitted afterward |
| --- | --- | --- |
| C0: Scope | Approve developer-agent change-control boundary. | WP-0/WP-1 only. |
| C1: Architecture | Approve ADRs, schemas, threat model. | WP-2/WP-3. |
| C2: Governance | Approve candidate-memory security and review workflow. | WP-4/WP-5. |
| C3: UX | Approve advisory developer flow. | WP-6. |
| C4: Operational | Approve rollout/SLO/rollback evidence. | WP-7/advisory launch. |
| C5: Brand | Choose public name after availability review. | Public rename and marketing only. |

**Recommended immediate next action:** approve C0, then implement only WP-0
(baseline harness) and WP-1 (schemas/canonicalization) with tests first. These
are additive and cannot alter the current enforcement decision path.
