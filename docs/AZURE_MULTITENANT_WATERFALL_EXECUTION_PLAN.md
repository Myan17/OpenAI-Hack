# Azure multi-tenant production — Waterfall execution plan

**Role:** Principal Engineering baseline  
**Lifecycle:** Requirements → Architecture → Detailed Design → Build → Integration → Verification → Release → Operations  
**Implementation status:** Planning only. This document authorizes neither Azure resource creation nor live Multica traffic.

## 1. Production definition

“Production ready” means more than a deployed demo. The release is production ready only when tenant isolation is enforceable at multiple layers, identity is verified, secrets are managed outside source control, every integration is retry-safe, recovery is rehearsed, and an operator can explain and reverse every consequential decision.

The first live integration remains **staging Multica + advisory-only**. It may report `continue_advisory`, `reviewer_required`, or `quarantine`; it may never execute, approve, mutate, or schedule external work.

## 2. Non-negotiable invariants

1. `interlock.engine` stays pure, deterministic, and dependency-free from cloud/identity/tenant services.
2. A request obtains tenant/workspace context from verified identity, never from user-controlled payload fields.
3. Every data query, evidence digest, event, export, callback, and cache key is workspace scoped.
4. Unknown tenant, unavailable authorization, ambiguous provenance, duplicate webhook, or unavailable evaluator fails closed to rejection/review/quarantine.
5. Customer prompts, source contents, secrets, and raw tool payloads are absent from metrics by default.
6. Every external callback is authenticated, idempotent, bounded, auditable, and separately retryable through an outbox.
7. A feature flag can disable any adapter/callback without disabling the existing enforcement demo.

## 3. Requirements traceability

| ID | Requirement | Design owner | Verification |
|---|---|---|---|
| PR-01 | Tenant and workspace scope are immutable. | Data | migration + cross-tenant negative tests |
| PR-02 | Identity derives scope from Entra claims. | Security | token/role/tenant mismatch tests |
| PR-03 | Tenant A cannot access tenant B data. | API | route/repository/RLS integration tests |
| PR-04 | Evidence is tenant-bound and tamper-evident. | Assurance | digest mutation and cross-scope replay tests |
| PR-05 | Staging callbacks are authenticated and idempotent. | Integration | signature/replay/outbox tests |
| PR-06 | Evaluator failure is non-permissive. | Reliability | fault injection |
| PR-07 | Tenant recovery is possible without cross-tenant restore. | Operations | restore drill |
| PR-08 | Logs and metrics are privacy-minimized. | Security | log/metric contract tests |
| PR-09 | Production changes are reproducible from IaC. | Platform | clean-environment deployment rehearsal |
| PR-10 | Existing local demo remains operational. | QA | regression/eval/browser checks |

## 4. Phase A — Requirements and governance

### Deliverables

- Data classification: identity, evidence, audit, operational, secret, and prohibited data.
- Tenant lifecycle: provisioned → active → suspended → deleted/retained.
- Workspace lifecycle and membership role matrix.
- Data-residency, retention, export, deletion, legal-hold, and support-access policies.
- Threat model and abuse-case catalog.
- RACI: product owner, security owner, platform owner, incident commander, on-call owner, privacy owner.

### Exit gate

Every PR requirement has an acceptance test, owner, and residual-risk decision. No cloud deployment begins before this gate.

## 5. Phase B — Architecture and detailed design

### 5.1 Logical components

```text
Browser/API client
   → Azure Front Door or approved ingress
   → Container App API (Entra token validation + TenantContext)
      → assurance service / deterministic engine
      → PostgreSQL tenant-scoped data
      → transactional outbox
      → callback worker (staging only)
      → Key Vault through managed identity
      → Azure Monitor (redacted telemetry)
```

### 5.2 Tenant data design

- `tenants(id, status, created_at, ...)`
- `workspaces(id, tenant_id, status, ...)`
- `memberships(tenant_id, workspace_id, subject_id, role, ...)`
- Add `(tenant_id, workspace_id)` to assurance cases, fixtures, audits, release evidence, correlations, idempotency receipts, and outbox records.
- Composite unique/index keys begin with scope. Foreign keys include parent scope where practical.
- Every production repository function accepts `TenantContext`; absence is a programmer error, not a default scope.

### 5.3 Migration strategy

1. Add nullable scope columns and control-plane tables.
2. Backfill the local/demo tenant/workspace through a migration script.
3. Add not-null, composite indexes, and scoped uniqueness only after validation.
4. Enable database isolation policy/RLS in staging; rehearse rollback.
5. Never rewrite/drop historical evidence during first production migration.

### 5.4 Identity and authorization

- Microsoft Entra JWT validation at API ingress/application boundary.
- Map immutable subject (`oid`/approved claim) to membership; never trust display name/email alone.
- Role checks: tenant admin, reviewer, developer, viewer, staging service.
- Service-to-service Azure access uses managed identity and least-privilege RBAC.
- Break-glass operations require audited, time-bounded approval.

### 5.5 Callback and outbox design

- Unique `(tenant_id, workspace_id, idempotency_key)` receipt before evaluation.
- Evidence creation and outbox enqueue share a database transaction.
- Worker uses capped exponential retry, dead-letter/quarantine state, and no duplicate callback emission.
- Callback body is the minimum advisory callback contract; no raw prompt/source data.
- Staging transport authentication details are abstracted behind an interface and omitted from local fixture mode.

### Exit gate

ADRs approved for tenancy model, RLS, identity claims, evidence scoping, outbox/idempotency, callback authentication, retention, and rollback.

## 6. Phase C — Build work packages

### C0: Tenant contracts and test fixtures

- Introduce strict `TenantContext`, tenant/workspace/membership schemas, and fixtures.
- Add tests for missing/invalid context and immutable scope.
- **Done:** no protected repository/API operation compiles or executes without context.

### C1: Scoped persistence and migrations

- Add additive schema migrations and scoped repositories.
- Backfill demo scope; preserve existing event/evidence data.
- **Done:** migration-up/migration-down/recovery tests pass against populated fixtures.

### C2: API authorization

- Add an injectable identity adapter: fixture identity locally, Entra validator in production configuration.
- Protect routes and implement role policy.
- **Done:** exhaustive same-tenant success and cross-tenant denial matrix passes.

### C3: Evidence, exports, and recovery scope

- Bind scope into evidence canonicalization and export/import manifests.
- Add tenant-safe export/restore implementation.
- **Done:** tenant A evidence cannot verify as tenant B; restore never overwrites another tenant.

### C4: Staging transport abstraction

- Implement transport protocol, local fake, receipt/idempotency store, transactional outbox, and callback worker test double.
- **Done:** duplicate, invalid, stale, unavailable, and callback-failure paths fail safely.

### C5: Azure IaC and runtime configuration

- Build parameterized Bicep/Terraform modules for network, Container Apps, PostgreSQL, Key Vault, ACR, Monitor, storage, and managed identities.
- Add policy validation, secret scanning, dependency pinning, and environment parameters.
- **Done:** a clean staging environment is reproducible without secret values in state/source.

### C6: Observability and operator surfaces

- Tenant-safe dashboard/admin views; aggregate metrics; alert rules; audit search constrained by role/scope.
- **Done:** operational dashboards distinguish tenant/system failures without exposing foreign tenant data.

### C7: Documentation and release automation

- API/transport contracts, onboarding, data handling, runbooks, release notes, rollback checklist, support playbook.
- **Done:** independent operator can deploy, diagnose, roll back, and restore from docs.

## 7. Phase D — Verification strategy

### Test pyramid

- Unit: claims mapping, tenant context, RLS query builders, canonicalization, idempotency, callback signer.
- Property/fuzz: malformed JWT claims, unknown workspace, scope substitution, envelope ordering, callback duplication.
- Migration: empty/populated/failed-upgrade/rollback/retry paths.
- Integration: API + scoped database + outbox + fake staging adapter.
- Security: cross-tenant enumeration, confused deputy, replay, forged callback, secret leakage, SSRF, privilege escalation.
- E2E: browser admin/reviewer/developer flows for two tenants.
- Reliability: evaluator outage, database failover simulation, callback retry/dead-letter, rate-limit/noisy-neighbor behavior.
- Recovery: tenant export/import, point-in-time restore, key rotation, feature-flag rollback.
- Performance: per-tenant and aggregate latency/load targets; capacity limits documented.

### Required release gates

1. Full existing test suite/evaluation/frontend build remains green.
2. Cross-tenant negative matrix is 100% green.
3. No unscoped production repository query is permitted by static/code-review rule.
4. IaC policy/security/dependency scans pass.
5. Staging callback replay/idempotency/failure tests pass.
6. Backup/restore and rollback drills have evidence and operator sign-off.
7. Security and privacy review approve residual risks.

## 8. Phase E — Azure deployment sequence

1. Provision isolated dev/staging resource groups from IaC.
2. Configure Entra/managed identities and Key Vault access, using placeholders until authorized.
3. Deploy database schema and application revisions with adapter/callback disabled.
4. Run smoke, migration, tenant-isolation, and recovery suites.
5. Enable fixture transport in staging; observe metrics.
6. Enable authenticated staging Multica callback for one allowlisted internal workspace.
7. Expand staging tenants only after a scheduled review of callback failures, quarantine rate, and privacy checks.
8. Production deployment is advisory-only and feature-flagged; no blocking rollout is implied.

## 9. Rollback and incident response

| Failure | Immediate action | Evidence |
|---|---|---|
| Cross-tenant suspicion | disable affected workspace/transport, preserve audit, incident response | access/query logs and evidence digests |
| Adapter/callback outage | disable callback flag, leave local assurance active | outbox/dead-letter records |
| Migration regression | stop rollout, restore approved backup/PITR, validate scope | migration and restore report |
| Key compromise | disable identity, rotate in Key Vault, invalidate service session | rotation audit |
| Unsafe advisory result | quarantine change class, create reviewed regression case | replay/evidence report |

## 10. Required authorization before deployment

The following must be supplied before any Azure mutation:

1. Azure subscription ID, allowed resource group(s), region, and budget owner.
2. Approved IaC tool and deployment identity/CI process.
3. Entra tenant, application/managed-identity ownership, and security administrator contact.
4. DNS/certificate/public ingress decision.
5. PostgreSQL sizing, data residency, RPO/RTO, backup retention, and encryption/key ownership requirements.
6. Staging Multica endpoint, authentication/signature specification, test workspace, rate limit, and callback contract.
7. Incident-response/on-call ownership and external support/escalation path.

## 11. Production sign-off checklist

- [ ] Architecture and ADR approval
- [ ] Tenant isolation penetration test approval
- [ ] Privacy/data retention approval
- [ ] IaC reproducibility and policy scan approval
- [ ] Staging transport reliability report
- [ ] Backup/restore and rollback rehearsal approval
- [ ] Monitoring/alerting/on-call approval
- [ ] Launch decision: advisory-only, scoped tenant allowlist

No checkbox may be implied by a successful local demo.
