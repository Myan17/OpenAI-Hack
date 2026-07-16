# rules.md — read before writing ANY line of code

Hard constraints for Interlock. These override convenience, cleverness, and any default habit.
If a task in the plan seems to require breaking one of these, stop and leave a
`# NOTE(interlock): <why>` instead of breaking it. Companion to `AGENTS.md` (read that for the
what/why; this is the what-you-must-not-do).

## The three inviolable rules (the product IS these)

1. **No model in the enforcement path.** `interlock/engine/**` must never import or call an LLM,
   HTTP client, or any network library. Allow/halt/escalate is computed by pure Python over a
   typed `Policy`. An LLM may draft a policy once in `intent.py`; that is the only place model
   output touches policy, and it happens offline before the agent runs.
   - Enforced by `tests/engine/test_purity.py`. If you make it fail, you broke the product.
2. **Fail closed.** Unknown tools, `UNKNOWN` reversibility, malformed input, and any branch the
   logic doesn't explicitly allow all resolve to **HALT**. When in doubt, block. The intent
   compiler's failure fallback is a **deny-all** policy, never an allow-all.
3. **Never gate reversible actions.** Reversible, in-scope actions always ALLOW and flow at full
   speed. Halting benign work recreates the approval-fatigue failure we exist to fix. Only
   actions that are *both* irreversible *and* out-of-intent may be halted.

## Stack — required

- **Python 3.13.** Type hints on every function. **Pydantic v2** models at every API/tool/agent
  boundary — no bare dicts crossing a boundary.
- **pytest** for all tests. **TDD is mandatory:** failing test first, then implementation.
- **FastAPI** for the backend. **SQLite** for the event log and sandbox DB.
- **OpenAI Agents SDK + GPT-5.6** for the demo agent and the one-shot intent compiler. This is
  an OpenAI hackathon — the agent and intent compilation must use GPT-5.6.
- **Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui** for the frontend. Server
  Components by default; client components only for the live feed / interactive controls.
- **LangFuse** for tracing (intent + verdicts only, never inside the engine).

## Stack — forbidden

- **No LangGraph, LangChain, CrewAI, or any agent framework** beyond the OpenAI Agents SDK. The
  flow is linear (intercept → classify → enforce); a graph framework is resume-driven noise.
- **No ML/LLM-based "is this malicious" classifier.** Reversibility and policy checks are rule
  based and deterministic. This is a design commitment, not a shortcut.
- **No raw scraping/browser automation** (Playwright/Puppeteer/requests-scraping). Not needed.
- **No second database** (no Redis, no Postgres for the hackathon). SQLite only.
- **No websocket framework.** Live updates are **SSE** from FastAPI. (Approval waits use
  `asyncio.Event` in-process.)

## Determinism & purity

- `interlock/engine/**` imports only the standard library + Pydantic. No `openai`, `anthropic`,
  `httpx`, `requests`, `urllib3`, `os.system` calls, or clock/random calls.
- **No `datetime.now()`, `time.time()`, or `random` inside `engine/`.** Timestamps are passed in
  from the caller (the event log stamps rows). This keeps enforcement reproducible and testable.
- Same `(action, policy)` in → same `Verdict` out, every time. If a change makes a verdict
  non-deterministic, revert it.

## Security & secrets

- **Never commit secrets.** `.env` is gitignored; `.env.example` is the committed template with
  empty values and comments. Verify `.gitignore` covers `.env`, `.env.local`, `.venv`,
  `node_modules`, `.next`, `*.sqlite`, `__pycache__` **before the first commit** of each area.
- The sandbox tools (`interlock/tools/sandbox.py`) act ONLY on a local temp SQLite DB, a temp
  directory under `/tmp/demo/`, and an in-memory ledger. They must never touch real files
  outside the sandbox, real networks, or real money. That is the whole point — they are
  dangerous *within a sandbox* so the breaker has something real to stop.
- Forbidden patterns and scope globs are the safety net; the sandbox boundary is the backstop.
  Both must hold.

## Testing & CI

- Every logic module has a test written first. Engine coverage is effectively total — every
  `enforce` branch has an asserting test.
- `python -m eval.run` must report `pass: True`. CI (`/.github/workflows/ci.yml`) **fails the
  build** if any golden known-bad action is allowed or any known-good action is halted. Do not
  weaken a scenario to make CI pass — fix the engine.
- Network-dependent tests (agent, intent) are `@pytest.mark.skipif` on missing API key so the
  suite runs offline.

## Git hygiene

- Conventional commits (`feat(engine): ...`, `test(api): ...`, `chore(web): ...`).
- Commit after every green step. Small commits, one deliverable each.
- When adding a new generated dir (e.g. `web/`), update `.gitignore` before the first commit.

## Verify before coding (do this once, at Task 9, before agent wiring)

Model/SDK details post-date parts of the training data — **confirm against current OpenAI docs,
do not assume:**
- the exact **GPT-5.6 model id** and that it is available in the OpenAI Agents SDK / Responses
  API;
- the **tool-call interception seam** — where the SDK surfaces a proposed tool call so
  `guarded_call` can gate it *before* the tool executes (this seam is load-bearing for the whole
  project);
- the **structured-output** mechanism used by `compile_policy`.
Record the confirmed model id in `.env.example`. If the SDK cannot expose a pre-execution
interception point, fall back to registering each tool handler as a `guarded_call` wrapper (the
handler itself calls `enforce` before doing anything) — never let a tool run unguarded.

## Scope discipline

Build in plan order. Do not start agent/UI work until Phase A (the pure engine) is green. If
time runs short, cut in this order: frontend polish → escalation flow → intent compiler
(hand-author a policy instead). **Never cut the engine or the eval gate** — they are the
submission.
