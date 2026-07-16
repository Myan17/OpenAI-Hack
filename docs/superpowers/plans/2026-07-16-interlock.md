# Interlock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Before writing any code, read `rules.md` and `AGENTS.md` at the repo root. Every task.**

**Goal:** Build Interlock — a runtime circuit breaker that deterministically halts irreversible, out-of-intent actions proposed by an autonomous AI agent, with a live decision feed and a CI-verified eval gate.

**Architecture:** A pure-Python deterministic enforcement engine (catalog → reversibility classifier → policy enforcer) is wrapped around an OpenAI Agents SDK agent's tool execution. Every decision is appended to an event log exposed over FastAPI+SSE and rendered live in a Next.js frontend. An LLM (GPT-5.6) only ever *drafts* a policy once, up front; it is never in the enforcement path.

**Tech Stack:** Python 3.13, Pydantic v2, pytest, FastAPI, OpenAI Agents SDK (GPT-5.6), SQLite, Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui, LangFuse, GitHub Actions.

## Global Constraints

- Python **3.13**; type hints on every function; Pydantic v2 models at all API/tool boundaries.
- The enforcement package (`interlock/engine/`) MUST import no network/LLM/HTTP client. A test enforces this.
- Enforcer is **fail-closed**: `UNKNOWN` reversibility and any unmatched branch resolve to `HALT`.
- TDD: every logic task writes the failing test first. Commit after every green step.
- No LangGraph, no ML-based classifiers, no raw scraping tools. See `rules.md`.
- Frontend: Server Components by default; client components only for the live feed. Tailwind + shadcn/ui only.
- Never commit secrets. `.env` is gitignored; `.env.example` is the committed template.

---

## Phasing (6 days, solo)

- **Day 1 — Phase A:** Deterministic engine (Tasks 1–6). The defensible core. No LLM, no network.
- **Day 2 — Phase B:** Agent + dangerous tools + interception seam + intent compiler (Tasks 7–11).
- **Day 3 — Phase C:** FastAPI, event log, SSE feed, escalation approve/reject (Tasks 12–15).
- **Day 4 — Phase D:** Next.js frontend — live feed, policy panel, attack trigger (Tasks 16–19).
- **Day 5 — Phase E:** Eval harness, golden scenarios, CI gate, LangFuse tracing (Tasks 20–23).
- **Day 6 — Phase F:** Demo hardening, recorded fallback, README, video, Codex session capture (Task 24).

Cut order if behind: frontend polish → escalation flow → intent compiler (hand-author the policy) → **never cut the engine or the eval gate.**

---

## Phase A — Deterministic Engine

### Task 1: Project scaffold + data model

**Files:**
- Create: `pyproject.toml`, `interlock/__init__.py`, `interlock/engine/__init__.py`, `interlock/engine/models.py`
- Test: `tests/engine/test_models.py`

**Interfaces:**
- Produces: enums `Reversibility{REVERSIBLE,IRREVERSIBLE,UNKNOWN}`, `Decision{ALLOW,HALT,ESCALATE}`; models `Policy`, `ProposedAction`, `Verdict` exactly as in the design spec §5.

- [ ] **Step 1: Write the failing test**

```python
# tests/engine/test_models.py
from interlock.engine.models import Policy, ProposedAction, Reversibility, Decision

def test_policy_defaults_are_failsafe():
    p = Policy(task="t", allowed_tools=set(), allowed_paths=[], allowed_db_ops=set(),
              spend_cap_cents=0, forbidden_patterns=[])
    assert p.spend_cap_cents == 0
    assert "DROP" not in p.allowed_db_ops

def test_proposed_action_roundtrip():
    a = ProposedAction(tool="bash", args={"cmd": "ls"})
    assert a.tool == "bash" and a.args["cmd"] == "ls"
```

- [ ] **Step 2: Run test to verify it fails** — `pytest tests/engine/test_models.py -v` → FAIL (module missing).
- [ ] **Step 3: Implement `interlock/engine/models.py`** with the enums and Pydantic v2 models from design spec §5 (copy them verbatim; add `model_config = ConfigDict(frozen=False)` on `Verdict`).
- [ ] **Step 4: Run test** → PASS.
- [ ] **Step 5: Commit** — `git commit -am "feat(engine): typed data model for policy, action, verdict"`.

### Task 2: Tool catalog + reversibility classifiers

**Files:**
- Create: `interlock/engine/catalog.py`
- Test: `tests/engine/test_catalog.py`

**Interfaces:**
- Consumes: `Reversibility` from Task 1.
- Produces: `classify(tool: str, args: dict) -> Reversibility`. Registry maps tool name → classifier fn. Built-in classifiers for `bash`, `db`, `transfer`, `fs_write`, `git`. Unknown tool → `UNKNOWN`.

- [ ] **Step 1: Write the failing test**

```python
# tests/engine/test_catalog.py
from interlock.engine.catalog import classify
from interlock.engine.models import Reversibility as R

def test_bash_read_is_reversible():
    assert classify("bash", {"cmd": "ls -la"}) == R.REVERSIBLE

def test_bash_rm_rf_is_irreversible():
    assert classify("bash", {"cmd": "rm -rf build/"}) == R.IRREVERSIBLE

def test_db_select_reversible_drop_irreversible():
    assert classify("db", {"sql": "SELECT * FROM users"}) == R.REVERSIBLE
    assert classify("db", {"sql": "DROP TABLE users"}) == R.IRREVERSIBLE

def test_transfer_always_irreversible():
    assert classify("transfer", {"cents": 1}) == R.IRREVERSIBLE

def test_unknown_tool_is_unknown():
    assert classify("teleport", {}) == R.UNKNOWN
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement `catalog.py`.** Classifiers use conservative pattern rules: `bash` irreversible if cmd matches any of `rm -rf`, `rm -r`, `>`, `dd `, `mkfs`, `git push --force`, `kill`, `shutdown`; else reversible. `db` reversible only for statements whose leading keyword is in `{SELECT, EXPLAIN, WITH...SELECT}`; `DROP/DELETE/UPDATE/TRUNCATE/ALTER/INSERT` → irreversible. `transfer` always irreversible. `fs_write`/`git` irreversible. Leading-keyword parse is uppercase-normalized and whitespace-stripped.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `git commit -am "feat(engine): reversibility classifiers for built-in tools"`.

### Task 3: Forbidden-pattern matcher

**Files:**
- Create: `interlock/engine/patterns.py`
- Test: `tests/engine/test_patterns.py`

**Interfaces:**
- Produces: `matches_forbidden(action: ProposedAction, patterns: list[str]) -> str | None` — returns the first matching pattern (for `matched_rule`) or `None`. Serializes the action to a stable string (`f"{tool} {json.dumps(args, sort_keys=True)}"`) before matching, case-insensitive.

- [ ] **Step 1: Write the failing test**

```python
# tests/engine/test_patterns.py
from interlock.engine.patterns import matches_forbidden
from interlock.engine.models import ProposedAction

def test_matches_drop_table():
    a = ProposedAction(tool="db", args={"sql": "drop table users"})
    assert matches_forbidden(a, [r"DROP\s+TABLE"]) == r"DROP\s+TABLE"

def test_no_match_returns_none():
    a = ProposedAction(tool="bash", args={"cmd": "ls"})
    assert matches_forbidden(a, [r"rm -rf"]) is None
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** with `re.search(pat, blob, re.IGNORECASE)`. **Step 4: Run** → PASS. **Step 5: Commit** — `git commit -am "feat(engine): forbidden-pattern matcher"`.

### Task 4: Scope checks (paths, db ops, spend)

**Files:**
- Create: `interlock/engine/scope.py`
- Test: `tests/engine/test_scope.py`

**Interfaces:**
- Produces: `path_in_scope(path, allowed_globs) -> bool` (uses `fnmatch`), `db_op_allowed(sql, allowed_ops) -> bool` (leading-keyword parse, shared helper with catalog — factor into `interlock/engine/sqlkw.py: leading_keyword(sql)->str`), `within_spend(cents, cap) -> bool`.

- [ ] **Step 1: Write failing tests** for: `/tmp/demo/x` in `["/tmp/demo/*"]` True; `/etc/passwd` False; `DELETE` not in `{"SELECT"}` False; `600 <= 500` False. (Write all four asserts.)
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** `sqlkw.py` + `scope.py`; refactor `catalog.py` to use `leading_keyword`. **Step 4: Run all engine tests** → PASS. **Step 5: Commit** — `git commit -am "feat(engine): scope checks for paths, db ops, spend"`.

### Task 5: Policy enforcer (the core)

**Files:**
- Create: `interlock/engine/enforcer.py`
- Test: `tests/engine/test_enforcer.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `enforce(action: ProposedAction, policy: Policy) -> Verdict`, implementing the six-step rule sequence in design spec §6 exactly, in that order.

- [ ] **Step 1: Write the failing test** (one assert per rule branch)

```python
# tests/engine/test_enforcer.py
from interlock.engine.enforcer import enforce
from interlock.engine.models import Policy, ProposedAction, Decision, Reversibility

def P(**kw):
    base = dict(task="t", allowed_tools={"bash","db"}, allowed_paths=["/tmp/demo/*"],
                allowed_db_ops={"SELECT","INSERT"}, spend_cap_cents=0, forbidden_patterns=[r"rm -rf /"])
    base.update(kw); return Policy(**base)

def test_tool_not_allowed_halts():
    v = enforce(ProposedAction(tool="transfer", args={"cents":100}), P())
    assert v.decision == Decision.HALT and v.matched_rule == "allowed_tools"

def test_forbidden_pattern_halts_before_reversibility():
    v = enforce(ProposedAction(tool="bash", args={"cmd":"rm -rf /"}), P())
    assert v.decision == Decision.HALT and v.matched_rule.startswith("forbidden_pattern")

def test_reversible_allows():
    v = enforce(ProposedAction(tool="bash", args={"cmd":"ls"}), P())
    assert v.decision == Decision.ALLOW and v.reversibility == Reversibility.REVERSIBLE

def test_db_drop_out_of_ops_halts():
    v = enforce(ProposedAction(tool="db", args={"sql":"DELETE FROM users"}), P())
    assert v.decision == Decision.HALT and v.matched_rule == "allowed_db_ops"

def test_irreversible_in_scope_escalates():
    v = enforce(ProposedAction(tool="db", args={"sql":"INSERT INTO users VALUES(1)"}),
                P(allowed_db_ops={"SELECT","INSERT"}))
    assert v.decision == Decision.ESCALATE and v.matched_rule == "irreversible_in_scope"

def test_unknown_tool_fails_closed():
    v = enforce(ProposedAction(tool="teleport", args={}), P(allowed_tools={"teleport"}))
    assert v.decision == Decision.HALT   # UNKNOWN reversibility → fail closed
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement `enforce`** following §6 exactly; every branch sets `reason` + `matched_rule`. **Step 4: Run** → PASS. **Step 5: Commit** — `git commit -am "feat(engine): deterministic policy enforcer"`.

### Task 6: Purity guard (the deterministic guarantee, as a test)

**Files:**
- Test: `tests/engine/test_purity.py`

- [ ] **Step 1: Write the test** that imports every module under `interlock/engine` and asserts none of `sys.modules` gained `openai`, `anthropic`, `httpx`, `requests`, `urllib3` as a result. Use a subprocess importing only the engine and dumping `sys.modules` keys.
- [ ] **Step 2: Run** → PASS (if it fails, a network import leaked into the engine — remove it). **Step 3: Commit** — `git commit -am "test(engine): assert enforcement path is network/LLM-free"`.

---

## Phase B — Agent, Tools, Interception, Intent

### Task 7: Sandbox tools (the dangerous surface)

**Files:**
- Create: `interlock/tools/sandbox.py`
- Test: `tests/tools/test_sandbox.py`

**Interfaces:**
- Produces: `run_bash(cmd)`, `run_db(sql)` (against a per-session SQLite file seeded with `users`,`sessions`), `transfer(cents, to)` (mutates an in-memory ledger), `fs_write(path, content)`, all returning `dict`. These are the *real* effects the enforcer guards. Each takes effect ONLY when called — the interceptor decides whether to call them.

- [ ] Steps: failing test that `run_db("SELECT count(*) FROM users")` returns a row and that `transfer(100,"x")` reduces the ledger; implement against a seeded temp SQLite; run → PASS; commit `feat(tools): sandbox tools with real local effects`.

### Task 8: Interceptor (wraps tool execution)

**Files:**
- Create: `interlock/interceptor.py`
- Test: `tests/test_interceptor.py`

**Interfaces:**
- Consumes: `enforce`, sandbox tools, an `EventSink` protocol (`emit(verdict: Verdict) -> None`).
- Produces: `guarded_call(action, policy, sink) -> dict`. On `ALLOW` → dispatch to the real tool and return its result. On `HALT` → return `{"blocked": True, "reason": ...}` WITHOUT dispatching. On `ESCALATE` → block pending approval (Task 15 supplies the wait; for now treat as HALT with `escalated=True`). Always `sink.emit(verdict)` first.

- [ ] Steps: failing test asserting a `HALT` verdict never invokes the underlying tool (spy/mock), an `ALLOW` does, and `sink.emit` is called exactly once per call. Implement. Run → PASS. Commit `feat: guarded tool interceptor`.

### Task 9: Agent wiring (OpenAI Agents SDK + GPT-5.6)

**Files:**
- Create: `interlock/agent.py`, `.env.example`
- Test: `tests/test_agent_smoke.py` (network-gated; skip if no key)

**Interfaces:**
- Produces: `build_agent(policy, sink)` returning an agent whose tool handlers are the sandbox tools **wrapped by `guarded_call`**, and `run_agent(agent, prompt) -> transcript`.

- [ ] **VERIFY FIRST:** confirm GPT-5.6 model id + Agents SDK tool-call interception seam against current OpenAI docs (see `rules.md` §"Verify before coding"). Record the exact model id in `.env.example`.
- [ ] Steps: implement wiring; smoke test behind `@pytest.mark.skipif(no key)` that the agent completes a trivial reversible task; commit `feat: agent wired through the interceptor`.

### Task 10: Intent compiler (GPT-5.6 → Policy, one-shot)

**Files:**
- Create: `interlock/intent.py`
- Test: `tests/test_intent.py`

**Interfaces:**
- Produces: `compile_policy(task: str) -> Policy` using GPT-5.6 structured output. The prompt instructs least-privilege defaults (empty `allowed_db_ops` unless the task implies writes; `spend_cap_cents=0` unless the task names a budget; always include baseline `forbidden_patterns`). Output validated into `Policy`; on validation failure, retry once then fall back to a **deny-all policy**.

- [ ] Steps: test with a stubbed model client that `compile_policy` returns a valid `Policy` and that a malformed model response yields the deny-all fallback (never raises). Implement. Run → PASS. Commit `feat: one-shot intent→policy compiler with failsafe fallback`.

### Task 11: End-to-end engine+agent integration test

**Files:**
- Test: `tests/test_e2e_local.py`

- [ ] Steps: with a hand-authored policy (no network), drive `guarded_call` through a scripted sequence of actions (benign + a `DROP TABLE` + an over-cap `transfer`) and assert the DB/ledger are untouched by the blocked ones and the event sink recorded the right verdicts. Commit `test: end-to-end local enforcement without network`.

---

## Phase C — API, Event Log, Feed, Escalation

### Task 12: Event log (append-only, SQLite)

**Files:** Create `interlock/api/eventlog.py`; Test `tests/api/test_eventlog.py`.
**Interfaces:** Produces `EventLog(db_path)` with `append(verdict) -> int` (returns id), `since(event_id) -> list[dict]`, implementing the `EventSink` protocol. Each row: id, ts (ISO, passed in — no `Date.now` inside pure code), tool, decision, reversibility, reason, matched_rule, args_json.
- [ ] Steps: failing test that `append` then `since(0)` returns the row; implement; PASS; commit `feat(api): append-only event log`.

### Task 13: FastAPI app + policy + run endpoints

**Files:** Create `interlock/api/main.py`; Test `tests/api/test_main.py` (use `TestClient`).
**Interfaces:** `POST /policy` (body: `{task}` → compiled Policy, returned for human confirm), `PUT /policy` (human-edited Policy), `POST /run` (body `{prompt}` → kicks the agent in a background task, streaming verdicts to the event log), `GET /events?since=` (poll fallback).
- [ ] Steps: failing `TestClient` test for `POST /policy` returns a Policy JSON and `GET /events?since=0` returns `[]` initially; implement; PASS; commit `feat(api): policy + run + events endpoints`.

### Task 14: SSE live feed

**Files:** Modify `interlock/api/main.py`; Test `tests/api/test_sse.py`.
**Interfaces:** `GET /stream` yields `text/event-stream`, one event per new verdict. Backed by the event log + an `asyncio.Queue`.
- [ ] Steps: test that a posted verdict shows up on the stream; implement with `StreamingResponse`; PASS; commit `feat(api): SSE decision stream`.

### Task 15: Escalation approve/reject

**Files:** Modify `interlock/api/main.py`, `interlock/interceptor.py`; Test `tests/api/test_escalation.py`.
**Interfaces:** `POST /escalation/{id}/approve|reject`. Interceptor's `ESCALATE` path now awaits an `asyncio.Event` keyed by verdict id; approve resolves it to dispatch, reject resolves to block.
- [ ] Steps: test that an escalated action stays blocked until approved, then dispatches; implement; PASS; commit `feat(api): human approve/reject for escalations`.

---

## Phase D — Frontend (Next.js 15 + shadcn)

### Task 16: Frontend scaffold
**Files:** `web/` via `create-next-app` (App Router, TS, Tailwind); add shadcn/ui; `.gitignore` check.
- [ ] Steps: scaffold; add shadcn `button card badge table`; commit `chore(web): next.js + tailwind + shadcn scaffold`. (Check `.gitignore` covers `node_modules`, `.next`, `.env*` before first commit — see `rules.md`.)

### Task 17: Live action feed (client component)
**Files:** `web/app/page.tsx` (RSC shell), `web/components/action-feed.tsx` (client, subscribes to `/stream`).
**Interfaces:** Each verdict row renders tool + args, a colored `Badge` (green ALLOW / red HALT / amber ESCALATE), the reason, and the matched rule.
- [ ] Steps: build the feed against a mocked event source first, then wire to SSE; commit `feat(web): live action feed with verdict badges`.

### Task 18: Policy panel
**Files:** `web/components/policy-panel.tsx`.
**Interfaces:** Shows the compiled Policy (allowed tools/paths/db-ops/spend cap/forbidden patterns), editable, `PUT /policy` on save.
- [ ] Steps: build; commit `feat(web): editable policy panel`.

### Task 19: "Unleash" demo controls + escalation buttons
**Files:** `web/components/run-controls.tsx`.
**Interfaces:** A task input, a "Run agent" button (`POST /run`), a prominent **"Inject attack"** toggle that seeds the prompt-injection scenario, and inline Approve/Reject buttons on ESCALATE rows.
- [ ] Steps: build; commit `feat(web): run controls, attack toggle, escalation buttons`.

---

## Phase E — Eval, CI, Tracing

### Task 20: Golden scenario set
**Files:** Create `eval/scenarios.yaml`; `eval/__init__.py`.
**Interfaces:** ≥15 adversarial actions (each `{action, policy, expect: HALT}`) covering: rm -rf, DROP/DELETE, over-cap transfer, out-of-scope path write, disallowed tool, force-push, injection payloads; ≥10 benign (`expect: ALLOW`) covering reads, in-scope inserts, ls, in-budget no-op.
- [ ] Steps: author the YAML; commit `test(eval): golden adversarial + benign scenario set`.

### Task 21: Eval runner + scorecard
**Files:** Create `eval/run.py`; Test `tests/eval/test_run.py`.
**Interfaces:** `run_eval() -> {halted_bad, missed_bad, blocked_good, allowed_good, pass: bool}`. `pass` is True iff `missed_bad==0 and blocked_good==0`. Prints a scorecard table.
- [ ] Steps: failing test on a tiny inline set; implement; run against `scenarios.yaml` → PASS (fix engine if any scenario fails); commit `feat(eval): runner + scorecard`.

### Task 22: CI gate (GitHub Actions)
**Files:** Create `.github/workflows/ci.yml`.
**Interfaces:** Job: install, `pytest`, then `python -m eval.run` — **fails the build if `pass` is False.** Matrix on py3.13. Cache pip.
- [ ] Steps: write workflow; push a branch; confirm the Action goes green; deliberately break one scenario to confirm it goes red; revert; commit `ci: fail build if any known-bad action is allowed`.

### Task 23: LangFuse tracing
**Files:** Modify `interlock/interceptor.py`, `interlock/intent.py`; `.env.example`.
**Interfaces:** Wrap the intent compilation and each verdict as a LangFuse span/event (guarded by env — no key → no-op). Never trace inside `interlock/engine/` (keeps the purity guard intact).
- [ ] Steps: add tracing behind a feature flag; verify traces locally; commit `feat: langfuse tracing for intent + verdicts`.

---

## Phase F — Demo, Docs, Submission

### Task 24: Harden + package the submission
**Files:** `README.md`, `scripts/seed_demo.sh`, `docs/DEMO.md`.
- [ ] Write `README.md`: what/why (the validated problem + the three-claim thesis), architecture diagram, setup, and the deterministic-guarantee note.
- [ ] Write `scripts/seed_demo.sh` that rebuilds the sandbox DB + temp dir + injection fixture in <10s. Run before every rehearsal.
- [ ] Write `docs/DEMO.md`: the exact 90-second script from design spec §7, with the fallback plan.
- [ ] Rehearse live; **record a fallback video** the moment the live demo works end-to-end.
- [ ] Record the final <3-min video (audio must cover how Codex + GPT-5.6 were used).
- [ ] Capture the **Codex Session ID** where core functionality was built (submission requirement).
- [ ] Commit `docs: readme, demo script, seed; submission-ready`.

---

## Self-Review (completed)

- **Spec coverage:** engine (T1–6), agent+tools+interception+intent (T7–11), API/log/feed/escalation (T12–15), frontend (T16–19), eval+CI+tracing (T20–23), demo/docs (T24) — every design-spec section maps to tasks. ✎
- **Types:** `Reversibility`/`Decision`/`Policy`/`ProposedAction`/`Verdict` defined in T1 and used unchanged downstream; `enforce`, `classify`, `guarded_call`, `compile_policy`, `EventLog`, `run_eval` signatures are consistent across tasks.
- **Determinism:** T6 purity guard + T23 "never trace inside engine" protect the core guarantee.
- **Fail-closed:** enforcer default-deny (T5) and deny-all intent fallback (T10) both tested.
