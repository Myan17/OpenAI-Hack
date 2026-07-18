# Interlock deep research memo — 18 July 2026

## Research question

Can Interlock become a globally useful developer product in the agentic / loop-engineering era, rather than a generic policy wrapper or hackathon dashboard? This review covered primary research, current standards, protocol specifications, vendor architectures, and competing approaches.

## Executive conclusion

**Yes, but only with a sharper product.** “MCP gateway + allow/deny policy + audit log” is already an active product category: Microsoft AGT, AWS AgentCore, Google Agent Gateway, Databricks Unity AI Gateway, agentgateway, and Permit all cover parts of it. Signed action receipts are also appearing independently.

Interlock should become the **assurance loop for consequential developer agents**: it authorizes each action deterministically, records authority and effect, and turns every block, escalation, failure, rollback, or reviewer correction into a reviewed regression case replayed before any agent, policy, tool, or model change is promoted.

The question it answers is not merely “was this call allowed?” It is: **“Which known failure patterns is this agent build protected against, and did the latest change regress any of them?”**

## Evidence and design consequences

### Hard boundaries are required

OWASP identifies excessive agency as the danger of tool access triggered by manipulated model output. OpenAI recommends layered guardrails together with authentication, authorization, access control, and conventional security. Microsoft observes that MCP itself has no pre-execution policy checkpoint; its own 60-prompt red-team reported a 26.67% prompt-only policy violation rate (vendor-reported, not universal).

- [OWASP LLM06](https://owasp.org/www-project-top-10-for-large-language-model-applications/2_0_vulns/LLM06_ExcessiveAgency.html)
- [OpenAI agent guide](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
- [Microsoft Securing MCP](https://developer.microsoft.com/blog/securing-mcp-a-control-plane-for-agent-tool-execution/)

**Decision:** preserve the repository’s pure, deterministic, fail-closed evaluator. A model can suggest policy or propose an action; it cannot decide or issue authority.

### Identity and delegation are part of every action

NIST explicitly identifies agent identity, human-agent delegation, authorization, auditability, non-repudiation, and injection impact reduction as open enterprise problems. OAuth Token Exchange already defines the `act` claim for delegation. Current cloud platforms are converging on separate agent identities plus propagated human context.

- [NIST concept paper](https://www.nccoe.nist.gov/sites/default/files/2026-02/accelerating-the-adoption-of-software-and-ai-agent-identity-and-authorization-concept-paper.pdf)
- [RFC 8693 OAuth Token Exchange](https://www.ietf.org/rfc/rfc8693.html)
- [AWS agent identity guidance](https://docs.aws.amazon.com/wellarchitected/latest/agentic-ai-lens/agentsec03.html)
- [Microsoft Entra agent identities](https://learn.microsoft.com/en-us/entra/agent-id/agent-identities)

**Decision:** authorization must bind named agent workload, delegated human principal, canonical action, asset/environment, scope/budget, policy version, provenance, and expiry—plus revocation and a kill switch.

### MCP/A2A are not full governance models

MCP defines protected-resource authorization and security guidance, while explicitly warning about discovery, session, token, and injection risks. Tool results crossing servers are untrusted. A2A offers interoperability but not a complete business authorization model. Google supports custom authorization extensions over parsed MCP attributes; AWS describes default-deny per-call policy and approval for mutations.

- [MCP security practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices)
- [MCP client practices](https://modelcontextprotocol.io/docs/develop/clients/client-best-practices)
- [A2A specification](https://google-a2a.github.io/A2A/specification/)
- [Google MCP authorization](https://docs.cloud.google.com/gemini-enterprise-agent-platform/govern/gateways/delegate-authorization)
- [AWS tool authorization](https://docs.aws.amazon.com/wellarchitected/latest/agentic-ai-lens/agentsec02-bp01.html)

**Decision:** ship native SDK and MCP proxy first. A2A authority propagation is an adapter, not a reason to build another agent framework.

### The proxy category is crowded

Microsoft AGT, AWS AgentCore, Microsoft Foundry, Databricks, Linux Foundation agentgateway, and Permit already deliver combinations of routing, authentication, policy, and telemetry.

- [Microsoft Foundry MCP governance](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/governance)
- [Databricks governed MCP services](https://learn.microsoft.com/en-us/azure/databricks/agents/agent-framework/mcp-services)
- [agentgateway](https://agentgateway.dev/docs/standalone/main/about/introduction/)
- [Permit MCP Gateway](https://agent.security/)

**Decision:** Interlock must not sell itself as “a gateway.” Its wedge is provider-neutral closed-loop assurance: portable authority/effect evidence plus replayable behavior regression across agent, policy, adapter, and model changes.

### Receipts are necessary but not unique

SLSA/in-toto give strong provenance patterns, while current products and drafts already propose signed agent-action receipts.

- [SLSA provenance](https://slsa.dev/spec/v1.2/provenance)
- [in-toto](https://in-toto.io/)
- [OWASP Agentic Skills solutions](https://owasp.org/www-project-agentic-skills-top-10/solutions.html)

**Decision:** use standard Ed25519/JWS-compatible signatures, canonical JSON, hashes, chaining, key rotation, and independent verification. Do not invent a proprietary identity or claim receipts alone are novel.

### The requested “memory” needs a strict security model

Persistent free-form agent memory is a documented injection surface: malicious experiences or documents can influence future sessions. It must not become a source of executable instructions or self-modifying policy.

- [MemoryGraft](https://arxiv.org/abs/2512.16962)
- [MPBench memory poisoning study](https://arxiv.org/abs/2606.04329)
- [OWASP memory/context poisoning](https://genai.owasp.org/2026/05/13/memory-is-a-feature-it-is-also-an-attack-surface/)

**Decision:** implement a typed, auditable **failure-memory corpus**:

`observed event → candidate case → canonicalized action/provenance → replay → reviewer approval → policy release → monitored result → expiry/review`

Candidate cases have no runtime authority and never enter an agent prompt. Only an approved, versioned policy rule or regression fixture can affect enforcement.

### Evaluation must measure safety, utility, and generalization

AgentDojo and AgentDyn show why realistic adversarial tool-use testing matters; later research warns that older benchmarks can be weak or saturated. Agent-SafetyBench reported no evaluated agent above 60 on its composite score. ToolPrivBench finds that prompt alignment does not reliably select the least-privilege sufficient tool. SWE-CI moves coding-agent evaluation from one-shot success toward maintainability.

- [AgentDojo](https://arxiv.org/abs/2406.13352)
- [benchmark critique](https://arxiv.org/abs/2510.05244)
- [AgentDyn](https://arxiv.org/abs/2602.03117)
- [Agent-SafetyBench](https://arxiv.org/abs/2412.14470)
- [ToolPrivBench](https://arxiv.org/abs/2606.20023)
- [SWE-CI](https://arxiv.org/abs/2603.03823)
- [Anthropic agent-evals guidance](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)

**Decision:** every policy/model/tool update requires an assurance regression gate: unsafe misses, safe work blocked, approval load, avoided blast radius, decision latency, and regression coverage—not a vanity count of blocked calls.

### Loop engineering makes assurance the right wedge

Current loop-engineering practice is closed feedback: agents plan, act, test, observe, and self-correct. It increases leverage but scales repeated mistakes and policy drift. This aligns with CI-oriented research and current evaluation tooling.

- [Loop engineering](https://loopengineering.run/)
- [SWE review loop research](https://arxiv.org/abs/2607.06065)
- [OpenAI AgentKit evaluation capabilities](https://openai.com/index/introducing-agentkit/)
- [OpenTelemetry GenAI agent/tool spans](https://github.com/open-telemetry/semantic-conventions/blob/main/model/gen-ai/spans.yaml)

**Decision:** expose a Loop Assurance Scorecard: enforced capability coverage, grant hygiene, known-failure replay coverage, safety/utility rates, approval/decision latency, budget use, receipt validity, and trace completeness.

## Revised product: Interlock Assurance Loop

### Core objects

1. **Authority Grant** — signed, expiring, attenuable delegation from a human/service principal to an agent for a task and asset/environment scope.
2. **Action Contract** — typed canonical operation plus reversibility, criticality, data/egress properties, budgets, and pre/postconditions.
3. **Decision Receipt** — signed policy evaluation with action/policy digests, result, reasons, obligations, approver, expiry, and key ID.
4. **Effect Receipt** — adapter-signed attempted/executed/failed/reverted result linked to the decision receipt.
5. **Assurance Case** — immutable regression fixture from a block, escalation, incident, reviewer correction, or desired behavior.
6. **Assurance Suite** — versioned cases evaluated in simulation and controlled integration environments before a policy, adapter, agent configuration, or model rollout.
7. **Assurance Report** — coverage, behavior delta, evidence, and release decision.

### Complete loop

```text
Agent proposes action
  → deterministic decision + receipt
  → adapter proves effect / non-effect
  → block, approval, failure, rollback, or reviewer correction
  → candidate assurance case
  → canonicalize + sanitize + replay across historical traces
  → human approves policy/case change
  → CI gates all future policy / agent / adapter changes
  → scorecard shows autonomy earned, not claimed
```

## Full implementation scope

### Authority and enforcement

- Preserve and strengthen the current pure reference evaluator.
- OIDC identity; OAuth Token Exchange/actor propagation; short-lived grants; revocation.
- Canonical GitHub, SQL, filesystem, CI, and later Kubernetes action contracts.
- Native SDK and MCP proxy, both default-deny.
- Exact-action approvals, dual control, expiry/replay protection, break-glass records.

### Evidence and verification

- Signed decision/effect receipts, hash chain, public-key/key-rotation model, canonical JSON.
- Evidence export plus standalone verifier CLI.
- Privacy-preserving OpenTelemetry with explicit sensitive-content capture opt-in.
- Trusted tool/adapter registry plus release provenance.

### Assurance memory and evaluation

- Candidate-case creation from blocked/escalated/reviewed events.
- Provenance, secret-redaction, human review, staged policy rollout, expiry, rollback, and ownership.
- Deterministic trace replay and effect-free simulation.
- Controlled adapter replay for poisoned tool definitions/results, stale grants, approval replay, privilege escalation, cost loops, and cross-tool taint.
- CI behavior-diff that refuses policy/agent/adapter regressions.

### Developer product

- CLI: `grant`, `simulate`, `replay`, `verify`, `diff`, `revoke`, `report`.
- Console: live decisions, exact approval, action/effect chain, case review, behavior diff, scorecard.
- GitHub Checks integration that attaches authority scope, policy impact, failed cases, and evidence to PRs.
- Demo: guarded issue → low-risk inspection → proposed migration/PR → approval → receipt/effect → poisoned issue blocked → reviewer correction becomes a future passing regression case.

### Deployment and operations

- Docker Compose local profile; Helm production profile; PostgreSQL/object store/KMS/OIDC/OTel.
- Backup/restore, key rotation, audit retention, budgets, load/chaos tests.
- Threat model, benchmark methodology, runbooks, SBOM/SLSA provenance, residual-risk report.

## Decisions before expansion code

1. Use existing standards where mature; do not invent agent identity.
2. Keep the typed evaluator portable; make OPA/Cedar optional backends behind an interface.
3. Start with GitHub, workspace, PostgreSQL, and CI; do not pretend to support every enterprise system first.
4. Never autonomously mutate policy from “learning.”
5. Publish exact safety, utility, evidence, and latency methodology; never claim universal injection prevention.

## Roadmap priority correction

1. Define the seven core schemas and receipt/assurance contracts.
2. Build the end-to-end developer adapters and effect receipts.
3. Build failure-memory, replay, CI behavior-diff, and scorecard.
4. Add MCP proxy and deployment/identity hardening in parallel once the reference path is reliable.

This is a complete, directly usable product direction with a coherent wedge—rather than a generic gateway clone—and it realizes the requested memory/guardrail vision safely.
