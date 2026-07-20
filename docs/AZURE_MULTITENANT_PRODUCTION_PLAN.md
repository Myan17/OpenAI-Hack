# Azure multi-tenant production implementation plan

**Status:** architecture and implementation baseline. Cloud deployment requires a separate, explicit Azure subscription/resource authorization and must not place credentials in this repository.

## Decision record

- Cloud: Azure.
- Data boundary: multi-tenant from day one.
- Initial external integration: staging Multica connection only.
- Enforcement: advisory-only.
- Trust rule: Interlock never performs a provider task mutation or external effect as part of its enforcement decision.

## Production outcome

Each organization receives an isolated workspace boundary. A request resolves one authenticated tenant before reading or writing any policy, candidate, replay, evidence, task correlation, or audit record. An advisory result may be delivered to a staging integration, but missing identity, tenant mismatch, unavailable evaluator, or invalid evidence must yield review/quarantine rather than continuation.

## Phase P0 — Requirements and tenant threat model

### Required invariants

1. Every persisted customer-owned entity has immutable `tenant_id` and `workspace_id`.
2. Tenant context is derived only from verified identity/claims, never body/query input.
3. Every repository query is tenant-scoped; cross-tenant access is a denial, not an empty success.
4. Evidence digests bind tenant/workspace identifiers to prevent replay across organizations.
5. Exports, restores, metrics, logs, and support operations preserve tenant boundaries.
6. Staging integration requests carry an idempotency key, correlation ID, authenticated provenance, and bounded retry policy.

### Abuse cases

- Caller substitutes another tenant ID in a route/body.
- A background worker omits tenant context.
- Evidence from tenant A is submitted as tenant B's callback.
- Shared database query lacks a tenant predicate.
- A staging webhook is replayed, unsigned, stale, or duplicated.
- One tenant exhausts shared resources or sees another tenant's metrics.

**Exit gate:** security review approves a tenant-isolation test matrix and data-classification inventory.

## Phase P1 — Tenant domain and authorization foundation

### Data model

| Entity | Fields added | Isolation rule |
|---|---|---|
| Tenant | immutable ID, name, lifecycle, plan | control-plane only |
| Workspace | immutable ID, tenant ID, name, status | belongs to exactly one tenant |
| Membership | tenant ID, workspace ID, subject ID, role | role checked before workspace access |
| Assurance case / fixture / audit | tenant ID, workspace ID | all reads/writes require matching context |
| Evidence / callbacks / correlations | tenant ID, workspace ID, idempotency key | digest includes scope |

### Roles

- `tenant_admin`: workspace and membership management.
- `assurance_reviewer`: review/retire cases and release evidence.
- `developer`: create candidate/evaluate advisory evidence.
- `viewer`: read verified evidence only.
- `service`: staging adapter only; least-privilege workspace assignment.

### Controls

- Central `TenantContext` dependency for every protected route.
- Repository APIs require context explicitly; no unscoped convenience methods.
- Database composite keys/indexes lead with `tenant_id, workspace_id`.
- Row-level security or equivalent database defense-in-depth for production store.
- Negative tests for every protected read/write route.

**Exit gate:** tests prove tenant A cannot read, mutate, replay, export, or verify tenant B’s records.

## Phase P2 — Azure platform foundation

### Target services

- Azure Container Apps: API and web workloads, staging/prod revisions, private ingress where appropriate.
- Azure Database for PostgreSQL Flexible Server: production relational store, private networking, high availability, encrypted backups.
- Azure Key Vault: staging integration secrets, callback signing keys, connection configuration.
- Microsoft Entra ID: workforce/service authentication and managed identities.
- Azure Container Registry: signed/traceable container images.
- Azure Monitor / Log Analytics / Application Insights: structured, redacted telemetry and alerting.
- Azure Storage: encrypted tenant-scoped exports/recovery artifacts with retention policy.

### Infrastructure as code

Provision with Bicep or Terraform, using separate resource groups/environments:

`dev → staging → production`

Required guardrails: tagged resources, least-privilege managed identities, private endpoints where available, deny-public-network policies for data services, secret references rather than secret values, budget alerts, diagnostic settings, locks on production data resources.

**Exit gate:** ephemeral staging environment can be recreated from IaC; policy scan reports no credential, public-data, or untagged-resource violation.

## Phase P3 — Staging Multica transport

### Transport contract

1. Receive a versioned envelope through an authenticated staging endpoint.
2. Verify signature/authentication, timestamp freshness, tenant/workspace mapping, replay/idempotency key, and schema version.
3. Persist a redacted correlation receipt scoped to tenant/workspace.
4. Evaluate through the deterministic local assurance path.
5. Deliver a minimal advisory callback with bounded retries and idempotency.

### Failure behavior

- Authentication/schema/tenant failure: reject and audit.
- Duplicate delivery: return prior callback without duplicate evaluation.
- Timeout/unavailable evaluator: callback `inconclusive` + `quarantine`.
- Callback delivery failure: durable outbox retry; never execute or approve an external task.

**Exit gate:** staging contract tests prove signature, replay, retry, tenant mismatch, and outage behaviors.

## Phase P4 — Operations and recovery

- Tenant-aware audit logs, evidence retention, export, deletion, and legal-hold procedures.
- Per-tenant rate limits, quotas, and noisy-neighbor alerts.
- Database backup, point-in-time restore, and tenant restore drills.
- Runbooks for tenant incident, callback outage, key rotation, compromised identity, evidence-verification failure, and regional recovery.
- SLOs: API availability, evaluator latency, callback delivery latency, evidence verification success, isolation violations (target zero).

**Exit gate:** restore and rollback drills are rehearsed; alerts and ownership are verified.

## Phase P5 — Rollout

1. Internal tenant only, staging Multica, advisory callbacks disabled by default.
2. Enable callback preview and observe evidence/transport metrics.
3. Enable advisory callback for allowlisted staging workspaces.
4. Add external tenants only after isolation, restore, rate-limit, and support runbooks pass.
5. Keep enforcement advisory-only until measured false-block/unsafe-miss targets and security review support a separate change class rollout.

## Authorization required before cloud changes

Before I can provision or deploy, provide/authorize:

1. Azure subscription and resource-group scope.
2. Azure region, billing owner, and naming/domain conventions.
3. Microsoft Entra tenant/app-registration approach and approved admin contact.
4. DNS/domain and certificate ownership for public ingress, if any.
5. Staging Multica endpoint, authentication specification, and test workspace—not production credentials in chat/repo.
6. Data residency, retention, support, and incident-response requirements.

Until those are supplied, I can implement tenant-safe application code, IaC templates with placeholders, tests, and operational documentation only.
