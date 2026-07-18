# Interlock

Interlock is a deterministic circuit breaker for autonomous-agent tool calls. It gives an agent
only a confirmed, least-privilege policy; then it decides every proposed action with plain,
reproducible policy-as-code—never another model.

> The seatbelt for AI agents: known authorized reads stay fast; unknown, forbidden, and
> out-of-intent actions stop before they touch a tool.

## Why it exists

Giving an agent tools means giving it the ability to change databases, write files, and move
money. Prompt instructions alone are not an authorization boundary: an agent can misunderstand
them or encounter adversarial text. Interlock reconciles each actual tool action with the
human-confirmed scope instead of trying to classify whether a prompt "looks malicious."

## The contract

1. **Intent, identity, and assets.** A typed policy defines permitted tools, database
   operations/tables, filesystem roots, GitHub operations/repositories, budget, forbidden
   patterns, agent identity, delegated human principal, environment, asset scope, criticality,
   and expiry.
2. **Known reads stay frictionless.** A recognized, authorized read is allowed immediately.
   Unknown, malformed, disallowed, and forbidden calls fail closed.
3. **The verifier is deterministic.** GPT-5.6 may draft a policy once. It is not imported by,
   called by, or consulted by the enforcement engine.

```text
task ──▶ GPT-5.6 policy draft ──▶ human confirms Policy
                                        │
GPT-5.6 agent ── tool call ──▶ deterministic Interlock engine ──▶ sandbox effect
                                   │             │
                                   │             └─ allow / halt / escalate
                                   └─ SQLite event log ─▶ FastAPI SSE ─▶ Next.js dashboard
```

The only effects in the demo are a local SQLite fixture, a contained local directory, and an
in-memory mock ledger. There is no shell tool, network effect, real transfer, or real database.

## Run it

Requirements: Python 3.13, Node 20+, and an OpenAI API key for the live agent and policy-draft
calls.

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
cp .env.example .env # add OPENAI_API_KEY only for the live demo
.venv/bin/python -m pytest -p no:cacheprovider -q
.venv/bin/python -m eval.run
```

Start the backend in one terminal and the dashboard in another:

```bash
.venv/bin/python -m uvicorn interlock.api.main:app --reload
cd web && npm install && npm run dev
```

Open `http://127.0.0.1:3000`, draft a policy, inspect it, explicitly confirm it, and run the
guarded agent. The **Policy simulator** replays a labeled staging developer-agent trace without
dispatching any effects, reporting safe actions allowed, unsafe actions stopped, false blocks,
unsafe misses, and impacted sessions. The **Learning guardrails** panel records a candidate from
a verified pattern; only a human-approved candidate is composed into future policies. The **Inject
attack prompt** control intentionally adds a `DROP TABLE` / transfer instruction to the agent
prompt; the event feed should show the deterministic halts.

In-scope irreversible actions deliberately emit `ESCALATE` rather than running automatically.
The dashboard’s **Approve** and **Reject** controls resolve the exact stored action only once;
approval re-validates it against its persisted policy before resuming the local sandbox effect.

## Evidence

`python -m eval.run` exercises 25 golden scenarios: 10 authorized benign reads and 15
adversarial, malformed, forbidden, or out-of-scope actions. The gate fails if any known-bad
action is not halted or a known-good action is blocked.

The engine purity test imports each `interlock.engine` module in a fresh process and asserts that
no model or network client is pulled into the enforcement path. Simulator traces are evaluated by
the same pure decision engine and never reach tool dispatch.

## Limits

This is a hackathon proof, not a production security product. The sandbox and GitHub-style adapter
are intentionally local, the policy compiler is conservative and falls back to deny-all on failure,
and in-policy irreversible actions currently return `ESCALATE` rather than executing automatically.
A production version would use cryptographic agent identity, a real MCP policy gateway, external
asset inventory, signed approvals, and tamper-evident audit exports.
