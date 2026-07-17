# Interlock

Interlock is a deterministic circuit breaker for autonomous-agent tool calls. It lets known,
policy-authorized reads run, escalates in-policy irreversible work, and halts unknown, forbidden,
or out-of-policy actions before the sandbox executes them.

## Run

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -p no:cacheprovider -q
.venv/bin/python -m eval.run
```

The enforcement engine imports no model or network client. The included sandbox limits effects to
its SQLite fixture, local root, and an in-memory ledger.

## Demo proof

The golden eval exercises permitted reads plus forbidden `DROP`, out-of-table deletes, and
over-cap transfers. The FastAPI app drafts a deny-all policy and requires explicit confirmation
before a run can begin.
