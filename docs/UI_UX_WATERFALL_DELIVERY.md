# Interlock UI/UX delivery record

## 1. Requirements baseline

The operator interface must make the deterministic safety boundary understandable in one screenful, provide a guided route through the live demo, and preserve every existing API interaction. It must not imply that the local demo is a production deployment or that a model controls enforcement.

### Acceptance criteria

1. The first viewport states Interlock's purpose, deterministic boundary, and local/demo posture.
2. The primary path follows the actual operating sequence: define task, draft policy, confirm policy, simulate or run.
3. Decision, assurance, evidence, and adapter surfaces remain accessible without removing any existing action.
4. `ALLOW`, `HALT`, and `ESCALATE` are distinguishable without relying on color alone.
5. The interface works at narrow widths, exposes names/states to assistive technology, and retains keyboard focus visibility.
6. Documentation accurately distinguishes implemented local controls from proposed Azure, Multica, and production work.

## 2. Information architecture

```text
Global navigation
  ├─ Command workflow
  │   ├─ Task
  │   ├─ Policy draft and explicit confirmation
  │   └─ Simulator / safety demo / guarded agent
  ├─ Assurance workspace
  │   ├─ Guardrail review
  │   ├─ Regression memory and replay
  │   ├─ Release evidence
  │   └─ Fixture adapter preview
  └─ Live activity
      ├─ Verdict stream
      └─ Agent run history
```

The primary workflow appears before advanced assurance. This mirrors operational risk: no release evidence, fixture callback, or learning candidate has authority until the explicit policy boundary is in place.

## 3. Visual-system decisions

- **Tone:** dark operational command center, not a consumer chat interface.
- **Hierarchy:** a high-contrast headline and small uppercase section kicker identify purpose and stage before dense controls appear.
- **Color semantics:** green supports allow/healthy status, coral supports halt/rejection, amber supports escalation/review, and blue represents primary interaction. Each verdict also has visible text and a border treatment.
- **Controls:** one consistent high-contrast action style, disabled-state opacity, and native focus rings.
- **Data density:** cards provide grouping, while article rows expose event and evidence detail with code treatment for exact payloads/digests.
- **Responsive behavior:** navigation condenses, controls stack, and typography scales without horizontal dependency.

## 4. Implementation traceability

| Requirement | Implementation |
| --- | --- |
| Explain the boundary immediately | Header, trust indicators, and local/demo language in `web/app/page.tsx` |
| Provide a guided primary path | Numbered workflow kickers and command panel before all advanced panels |
| Preserve the operational surface | Existing handlers, endpoints, state, and evidence controls remain unchanged |
| Accessibility | Semantic navigation/headings, named form controls, `aria-live` status, and visible `:focus-visible` styles |
| Professional repository presentation | README quick start, capability boundary, architecture, verification, deployment posture, and repo map |

## 5. Verification record

Visual/browser verification exercised the live local dashboard and confirmed that the accessible tree exposes named navigation, task entry, draft/confirm/simulate controls, disabled sequencing, verdicts, assurance controls, evidence controls, and run history. The interactive regression successfully completed draft → confirm → simulate.

Release gates executed after the presentation changes:

```text
pytest: 149 passed, 1 skipped (explicit live-agent opt-in)
golden evaluation: 15 unsafe halted, 0 unsafe missed, 0 safe blocked, 10 safe allowed
frontend build: passed
```

## 6. Deferred work

The UI does not turn the local prototype into a deployed security service. Real tenant identity, Azure resources, external Multica transport, credentials, live callbacks, and enforcement beyond advisory mode remain separately authorized deployment work. Their design constraints live in the Azure and Multica runbooks.
