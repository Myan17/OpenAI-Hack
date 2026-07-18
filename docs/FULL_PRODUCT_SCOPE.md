# Interlock: Full Product Scope and Research-Grounded Plan

**Status:** architecture and delivery plan. No implementation in this document changes the
current deterministic enforcement contract.

## 1. Product decision

Interlock becomes an **open agent authorization control plane** for developer agents. It
evaluates every proposed consequential action before execution, independently from the model
that proposed it, and returns a reproducible allow, halt, or approval-required decision.

It is not a prompt-injection classifier and it is not an observability dashboard. Its durable
unit of value is an **action authority receipt**:

`who (agent + delegated human) may do what action to which asset, in which environment, under
which policy and contextual constraints, until when, with what approval, and what actually
happened.`

The initial use case is developer agents working across GitHub, databases, filesystems, CI/CD,
and cloud/Kubernetes APIs. The architecture remains adapter-based so the same authority model can
serve support, finance, security operations, and data workflows later.

## 2. Research synthesis and product implications

| Finding | Evidence | Interlock design consequence |
| --- | --- | --- |
| Prompt injection and excessive agency turn ordinary tool access into consequential risk. | [OWASP LLM06](https://owasp.org/www-project-top-10-for-large-language-model-applications/2_0_vulns/LLM06_ExcessiveAgency.html), [OWASP Agentic Top 10](https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/) | Put a deterministic policy-enforcement point immediately before each effect; never delegate the final decision to the model. |
| Identity, delegated authority, authorization, auditability, and prompt-injection impact reduction are open enterprise problems—not solved by a chat prompt. | [NIST agent identity concept paper](https://www.nccoe.nist.gov/sites/default/files/2026-02/accelerating-the-adoption-of-software-and-ai-agent-identity-and-authorization-concept-paper.pdf) | Bind every decision to workload identity, agent identity, human principal, session, environment, asset, expiry, and policy version. |
| MCP supplies transport-level authorization, but it is not a complete action-governance layer. Tool discovery, output, and cross-server data flows remain risky. | [MCP authorization](https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization), [MCP security practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices), [MCP client practices](https://modelcontextprotocol.io/docs/develop/clients/client-best-practices) | Build an MCP gateway/proxy and native SDK as enforcement points; verify server identity and schemas, treat tool results as untrusted, and enforce independently of tool annotations. |
| Workload identities need attestable, short-lived credentials rather than shared agent API keys. | [SPIRE concepts](https://spiffe.io/docs/latest/spire-about/spire-concepts/) | Support OIDC first; add SPIFFE/SPIRE workload identity in production deployment profiles. Use short-lived tokens and revocation. |
| Policy decision points and policy enforcement points are established architecture; policy must be analyzable and versioned. | [OPA deployment](https://www.openpolicyagent.org/docs/deploy), [Cedar authorization](https://docs.cedarpolicy.com/auth/authorization.html), [Cedar validation](https://docs.cedarpolicy.com/policies/validation.html) | Preserve the current typed, pure core as the reference evaluator. Add a policy compiler/validator and decision bundle format. Evaluate fail-closed at the local enforcement point. |
| Provenance must be independently verifiable; ordinary mutable logs do not establish non-repudiation. | [SLSA provenance model](https://slsa.dev/spec/v1.2/provenance), [in-toto](https://in-toto.io/) | Sign receipts, chain audit records, snapshot the policy/input digest, and export verifiable evidence. |
| Existing prompt-injection benchmarks can be saturated or miss realistic adaptive attacks. | [AgentDojo](https://arxiv.org/abs/2406.13352), [benchmark critique](https://arxiv.org/abs/2510.05244), [AgentDyn](https://arxiv.org/abs/2602.03117) | Interlock’s evaluation cannot claim safety from a single benchmark. Maintain versioned adversarial traces, adaptive tests, utility tests, replay tests, and domain-specific failure injection. |
| Task alignment and tool-boundary enforcement are complementary approaches. | [Task Shield](https://arxiv.org/abs/2412.16682), [runtime tool-boundary enforcement](https://arxiv.org/abs/2604.11790) | Use task/policy compilation only before execution; runtime allows only machine-checkable, typed authority. Never infer intent from hostile runtime content. |

The supplied Meta engineering article reinforces a particularly useful operating model: measure
agentic friction (affected sessions/turns, blocked actions, and rule churn), not only blocked
requests. Interlock will make this a first-class operations view.

## 3. Product position and differentiation

**Not CausalOps.** CausalOps addresses evidence-backed causal reasoning for cyber decisions.
Interlock governs whether an agent may execute a side effect. They can integrate: a CausalOps
finding may become evidence attached to an Interlock approval, but it never replaces authority.

**Not an agent framework.** Interlock has no planner, memory, or model lock-in. It governs
Agents SDK, CLI coding agents, custom applications, and MCP clients at the action boundary.

**Not a generic IAM clone.** IAM answers whether an identity has broad access. Interlock adds
per-run delegated purpose, typed action semantics, criticality, taint/provenance, spend/rate
budgets, approval, and a signed decision/effect record.

**The defensible wedge:** developer-agent change control. A coding agent can inspect an issue and
repository with low friction, but a branch creation, PR, merge, migration, secret read, cloud
deployment, or destructive database operation has narrowly scoped, expiring, attributable
authority.

## 4. Full functional scope

### Control plane

1. **Identity and delegation service.** OIDC users, service/workload identities, agent
   registration, signed delegation grants, short TTL, revocation, and environment binding.
2. **Asset and tool catalog.** Registered tool schemas, publisher/server provenance, resource
   selectors, data classification, reversibility, criticality, egress capability, and risk tier.
3. **Policy authoring and lifecycle.** Typed policy DSL, policy templates, natural-language draft
   as a non-authoritative suggestion, linting, diff, dry-run, simulation, reviewer approval,
   staged rollout, immutable versioning, and rollback.
4. **Decision service.** Deterministic typed evaluator that returns `allow`, `halt`, or
   `escalate`, a machine-readable reason graph, obligations, policy/input digests, and a
   single-use authority receipt. The local gateway must fail closed when disconnected.
5. **Approval service.** Exact-action approvals with canonical rendering, dual control for high
   criticality, expiry, approval binding to input digest, and out-of-band confirmation surface.
6. **Evidence service.** Append-only hash-chained events, receipt signing, policy and action
   snapshots, effect acknowledgments, retention, export, and independent verifier CLI.
7. **Learning workflow.** Candidate guardrails arise from a blocked action, incident, or
   simulation. They remain inactive until linted, replayed against regression suites, reviewed,
   and promoted. No autonomous self-modification of enforcement policy.

### Enforcement plane

1. **Python SDK.** Typed tool decorator/client for native applications; no raw `dict` action
   boundary. It verifies a receipt immediately before dispatch and reports the effect outcome.
2. **MCP gateway.** JSON-RPC proxy that authenticates client/server, pins trusted server/tool
   manifests, validates schemas, requests a decision for every `tools/call`, gates response
   forwarding, and records the complete authority chain.
3. **Developer adapters.** GitHub, PostgreSQL, filesystem/workspace, CI/CD, Kubernetes, and
   cloud deployment adapters. Each uses constrained verbs, canonical resource selectors, and a
   safe test double. No general shell capability.
4. **Context provenance/taint.** Label source material as user, repository, issue, tool result,
   web, memory, or system. Taint never grants authority; policies may prohibit tainted paths from
   reaching egress, secret, merge, or destructive tools without an independent approval.
5. **Local resilience.** Signed policy bundles and public keys cached at the enforcement point;
   offline decisions only for explicitly permitted low-risk reads; all other calls fail closed.

### Operator experience

1. **Web console.** Live agent map, decision feed, policy editor/diff, simulation, approval
   inbox, asset/tool inventory, incident timeline, guardrail review, and friction metrics.
2. **CLI.** Register agent/tool, validate policy, simulate trace, issue/revoke grant, inspect a
   receipt, verify an evidence export, and run an integration test suite.
3. **Observability.** OpenTelemetry-compatible traces correlate agent run, decision, tool call,
   approval, and effect without exporting sensitive prompt/tool content by default. Metrics:
   unsafe misses, false blocks, decision latency, approval latency, affected sessions, affected
   turns, policy coverage, guardrail churn, and receipt verification failures.

## 5. Authorization model and invariants

An authorization request is a normalized tuple:

`(agent identity, delegated human, session, action verb + typed arguments, asset selector,
environment, criticality, provenance/taint, budgets, time, policy version, approval receipt)`.

The decision model is **deny-overrides and fail-closed**:

- unknown identity, tool, schema, asset classification, freshness, or policy → `HALT`;
- known read that is within authority and not taint-restricted → `ALLOW`;
- in-authority consequential action requiring confirmation → `ESCALATE`;
- all effects require a short-lived, single-use receipt; an adapter rechecks the receipt and
  canonicalized action immediately before executing;
- a model can propose a policy or action but can never generate authority, approval, asset facts,
  or a decision;
- tool output, issue text, documents, repository content, and memory are data, not authority.

The present `interlock.engine` remains the pure reference implementation. It must retain the
existing invariant: no network/model/clock/random dependency and identical typed input produces
identical verdict.

## 6. Threat model

Interlock protects against model mistakes, direct and indirect prompt injection, poisoned tool
descriptions/results, memory/context poisoning, confused deputy delegation, stale/broad tokens,
scope creep, over-budget loops, replayed approvals, malicious or compromised MCP servers, unsafe
cross-tool data flow, and post-incident denial.

It does **not** make a compromised host, stolen signing key, malicious authorized human, or a
vulnerable destination system safe. Those risks require conventional endpoint, key-management,
network, and destination authorization controls. Interlock also must never claim that a policy
proves a task was semantically beneficial; it proves which deterministic authority check occurred.

## 7. Architecture

```text
                         Control plane
  Console/CLI ──> Policy, Identity, Asset, Approval, Evidence APIs
                              │ signed policy bundles / public keys
                              ▼
Agent SDK ───────────────> Interlock enforcement point ──> typed adapter ──> effect
MCP client ──────────────> MCP gateway / enforcement point ──> MCP server
                              │          │                 │
                              │          ├─ decision receipt ─┤ effect acknowledgement
                              │          └─ OTel + hash-chained evidence
                              ▼
                  deterministic reference evaluator
```

Logical services may run as a modular monolith for the demo, but their interfaces must be stable
enough to split at production scale. The first deployable profile is Docker Compose; the
production profile is Helm/Kubernetes with OIDC, optional SPIRE, external PostgreSQL/object
storage, an OTel collector, and a managed KMS/HSM.

## 8. Delivery plan and release gates

### Phase 0 — Architecture baseline (current planning stage)

- Freeze the authority tuple, receipt schema, policy DSL, adapter contract, threat model, and
  public compatibility policy.
- Add architecture decision records for Cedar/OPA vs reference evaluator, signing format,
  identity provider abstraction, and persistence/deployment topology.
- Gate: independent design review confirms the existing pure engine invariants remain intact.

### Phase 1 — Production-grade core

- Extract stable domain packages: identity, catalog, policy, decision, receipt, evidence.
- Add canonical action normalization, policy validation/linting, versioning, signed single-use
  receipt verification, expiry/replay protection, and tamper-evident evidence chain.
- Move from demo-only SQLite to a production storage abstraction while retaining SQLite local
  mode; add migrations, retention, and export verifier.
- Gate: property/fuzz tests, deterministic replay, receipt tamper/replay tests, migration tests,
  and unchanged existing evaluation gate.

### Phase 2 — Developer-agent enforcement

- Ship Python SDK plus GitHub, PostgreSQL, filesystem, and CI adapters using safe test doubles.
- Build MCP gateway with OAuth/OIDC validation, trusted-server registry, tool schema pinning,
  request/response provenance, and policy decision interception.
- Gate: end-to-end test matrix proves every consequential adapter action is denied without a
  receipt and cannot bypass the gateway/SDK.

### Phase 3 — Human control and operations

- Implement delegated grants, approval inbox, dual-control threshold policies, break-glass
  workflow, revocation/kill switch, policy rollout/rollback, incident timeline, and verifier CLI.
- Gate: approval forgery, stale approval, noncanonical display, privilege escalation, and
  kill-switch chaos tests.

### Phase 4 — Context, supply chain, and learning

- Add source provenance/taint propagation, policy obligations for data-to-egress paths,
  MCP/tool publisher attestation, manifest review, and signed adapter release provenance.
- Upgrade candidate guardrails into a governed change workflow: candidate → simulator/evaluation
  report → reviewer → staged policy release → monitoring → rollback.
- Gate: poisoned issue/document/tool-result tests cannot create egress, destructive, merge, or
  secret authority; learned rule promotion is impossible without review and evidence.

### Phase 5 — Evaluation, deployment, and adoption

- Build an open `interlock-evals` corpus: benign developer workflows, policy abuse, injection,
  tool poisoning, confused deputy, scope creep, stale authority, and recovery scenarios.
- Test against AgentDojo/AgentDyn-style adapters where licensing permits, plus Interlock’s own
  realistic developer traces. Publish security, utility, latency, and friction methodology.
- Deliver Compose, Helm, Terraform examples, OTel/Grafana dashboards, SSO setup, backup/restore,
  key rotation, load/chaos tests, SDK documentation, and reference demo environments.
- Gate: reproducible deployment, signed artifacts, SBOM/provenance, restore drill, load target,
  threat-model review, and documented residual risk.

## 9. Hackathon demonstration that represents the real product

The demo should feel like a product, not a scripted chat:

1. A developer assigns an incident task and grants an agent narrow staging authority.
2. The agent reads GitHub and the staging schema through the MCP gateway; this is fast and
   visibly authorized.
3. A poisoned issue/tool result tries to make it exfiltrate a secret, merge a PR, or drop a table.
   The gateway halts it because no receipt/policy permits the typed action—not because a model
   guessed that text was malicious.
4. The agent proposes a legitimate migration. Interlock renders the exact canonical action,
   requests approval, signs a one-time receipt, executes through the adapter, and records the
   effect acknowledgment.
5. The console replays the full decision and independently verifies its evidence chain. A
   candidate guardrail is simulated against past traces before a reviewer promotes it.

## 10. Scope discipline

“Entire scope” means every critical product path above is specified and built to a deployable,
testable standard. It does not mean pretending a solo project can operate every enterprise
integration or run a global SaaS on day one. The first complete release has a real gateway, real
identity/delegation model, receipts, evidence, approvals, a robust adapter set, deployment
artefacts, and a reproducible evaluation suite. Additional adapters are plug-ins against those
same contracts, not bespoke features.

Before implementation begins, the next decision is to turn this scope into ADRs and an ordered
test-first execution backlog, preserving the current local demo as a compatibility fixture.
