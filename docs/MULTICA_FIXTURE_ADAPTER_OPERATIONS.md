# Fixture adapter operations

## Boundary

The current Multica-shaped adapter is fixture-only. It has no client library,
daemon control, credential, webhook, network call, or external task mutation.
Its output is advisory evidence and a callback preview only.

## Metrics

`/assurance/metrics` may expose `adapter:continue_advisory`,
`adapter:reviewer_required`, or `adapter:quarantine`. These are fixed labels;
task IDs, run IDs, prompts, repository names, traces, and payloads are never
metric dimensions.

## Recovery

Existing assurance snapshot export/import preserves cases, fixtures, and audit
history. The adapter itself is stateless: recreate a result by re-evaluating
the same versioned envelope, baseline, and replay fixture.

## Incident response

If a fixture adapter result is surprising, keep the evidence bundle, retire the
relevant active case if necessary, and rerun locally. Do not add a bypass or
turn an inconclusive callback into continuation. Any real provider transport is
a separate authorized integration with authentication, idempotency, and
rollback review.
