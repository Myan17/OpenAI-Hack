# Assurance operations runbook

## Scope

This runbook governs the report-only Developer-Agent Change Control layer. It
does not authorize changes to `interlock.engine`, agent tool dispatch, or the
local sandbox. The runtime enforcement demo remains independently available if
assurance is unavailable or disabled.

## Health and rollout

- Runtime health: `GET /health` must return `{"status":"ok"}`.
- Assurance health: `GET /assurance/health` returns either `ok` or `disabled`,
  always with `mode: report_only`.
- Aggregate, privacy-minimized counters: `GET /assurance/metrics`.
- Disable assurance by constructing the app with `assurance_enabled=False`.
  Assurance endpoints return `503`; `/health`, policy confirmation, simulator,
  demo, and deterministic action enforcement continue to work.

The assurance layer is advisory. A future blocking rollout requires measured
false-block and unsafe-miss evidence plus a separate approval.

## Standard release review

1. Capture baseline and candidate manifests.
2. Run a semantic authority diff.
3. Confirm every active case has an approved local replay fixture.
4. Replay fixtures; mixed trials are `inconclusive`, never a pass.
5. Assemble and verify an evidence bundle.
6. Generate the advisory check payload with `POST /assurance/check` or the
   local adapter.
7. Record any explicit human override outside the runtime policy path.

The standalone verifier is:

```bash
.venv/bin/python -m interlock.assurance.cli verify evidence-bundle.json
```

Exit status `0` means valid evidence, `1` means evidence failed verification,
and `2` means unreadable/malformed input.

## Candidate memory operations

- New candidate: `POST /assurance/candidates`; status is `pending_review`.
- Approval/rejection requires a reviewer identity.
- Only `active` cases may receive fixtures or replay.
- Cases can expire using explicit caller-supplied time through
  `POST /assurance/candidates/expire`.
- Audit history is append-only at
  `GET /assurance/candidates/{case_id}/history/audit`.
- Candidate summaries containing secret-like or email-like data are rejected
  before storage. Redact externally, then create a minimal replacement.

Never place raw incident text, secrets, user data, or an unreviewed candidate
into an agent prompt, a policy, or the deterministic engine.

## Recovery

### Assurance API/UI malfunction

1. Set `assurance_enabled=False`.
2. Verify `/health`, `/policy`, `/simulate`, and `/demo` still work.
3. Preserve SQLite evidence for diagnosis; do not silently delete records.
4. Re-enable only after the focused test, full pytest suite, safety evaluation,
   and frontend build are green.

### Invalid evidence bundle

1. Treat the release as `inconclusive`.
2. Do not promote from a failed verification result.
3. Preserve the original artifact and recompute a new bundle from canonical
   manifests/replay results.

### Sensitive candidate data

1. Disable new candidate capture if systemic.
2. Do not copy the sensitive value into logs, issue comments, fixtures, or
   prompts.
3. Replace the candidate with a redacted behavioral description.
4. Follow the host organization’s secret rotation and incident process when
   applicable.

## Release gate

Before an externally visible demo or release:

```bash
.venv/bin/python -m pytest -p no:cacheprovider -q
.venv/bin/python -m eval.run
cd web && npm run build
```

The demo may be shown only if the evaluation reports zero unsafe misses and
zero safe actions blocked. Current report-only assurance must never weaken this
baseline.

## Residual risk

This local profile does not provide production identity, KMS-backed signing,
tenant isolation, live GitHub installation, external MCP trust, backup/restore
infrastructure, or managed monitoring. Those need separate production design,
credentials, and authorization before implementation.
