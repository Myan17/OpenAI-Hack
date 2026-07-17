# Demo script

1. Draft and confirm a policy to inspect and clean `sessions`.
2. Show a green, allowed `SELECT` verdict.
3. Trigger the injection fixture: `DROP TABLE users` and an over-cap transfer.
4. Show both red halt verdicts and that the sandbox data and balance are unchanged.
5. Run `python -m eval.run` and show the passing scorecard.
