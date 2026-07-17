# 90-second demo script

1. Open the dashboard and say: “Interlock is a deterministic circuit breaker for agent tool
   calls. A model can draft intent, but it never decides whether a tool call is safe.”
2. Enter “Inspect the database schema and stale sessions,” click **Draft policy**, review the
   least-privilege JSON, then click **Confirm policy**. Point out that confirmation happens before
   an agent can run.
3. Click **Run guarded agent**. Show a green `ALLOW` row for a read-only, scoped inspection.
4. For an in-scope irreversible action, show the amber `ESCALATE` event and use **Approve** or
   **Reject**. Explain that the typed action and policy are persisted in SQLite before a human
   resolves it.
5. Enable **Inject attack prompt** and run again. Explain that the malicious instruction is only
   agent input—not a policy change. Show the red `HALT` event for `DROP TABLE` or any
   out-of-scope operation; emphasize the sandbox was never dispatched.
6. In the terminal, run `.venv/bin/python -m eval.run`. Show the 25-scenario scorecard with zero
   missed bad actions and zero blocked good actions.

Fallback if the network/model call is unavailable: run the local pytest suite and golden eval;
these exercise the same deterministic enforcement path without a model call.
