"""Minimal HTTP surface for policy confirmation and the audit feed."""

from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

import json

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from interlock.api.eventlog import EventLog
from interlock.engine.enforcer import enforce
from interlock.engine.models import Decision, EnforcementContext, Policy
from interlock.interceptor import dispatch_after_approval
from interlock.intent import compile_policy_with_openai
from interlock.tools.sandbox import Sandbox


AgentRunner = Callable[[Policy, str, EventLog, Path], Awaitable[str]]
PolicyCompiler = Callable[[str], Awaitable[Policy]]


class TaskRequest(BaseModel):
    task: str


class RunRequest(BaseModel):
    prompt: str


class PolicyUpdate(Policy):
    confirmed: bool = False


@dataclass
class AppState:
    event_log: EventLog
    sandbox_root: Path
    agent_runner: AgentRunner
    policy_compiler: PolicyCompiler
    policy: Policy | None = None
    confirmed: bool = False


def create_app(
    event_log: EventLog,
    agent_runner: AgentRunner | None = None,
    policy_compiler: PolicyCompiler | None = None,
) -> FastAPI:
    """Create an app with injected persistence, making HTTP tests isolated."""

    app = FastAPI(title="Interlock")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type"],
    )
    state = AppState(
        event_log=event_log,
        sandbox_root=event_log.db_path.parent / "sandbox",
        agent_runner=agent_runner or _run_local_agent,
        policy_compiler=policy_compiler or compile_policy_with_openai,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        """Return a dependency-free readiness signal for local orchestration."""

        return {"status": "ok"}

    @app.post("/policy", response_model=Policy)
    async def draft_policy(request: TaskRequest) -> Policy:
        state.policy = await state.policy_compiler(request.task)
        state.confirmed = False
        return state.policy

    @app.put("/policy", response_model=PolicyUpdate)
    def confirm_policy(update: PolicyUpdate) -> PolicyUpdate:
        state.policy = Policy.model_validate(update.model_dump(exclude={"confirmed"}))
        state.confirmed = update.confirmed
        return update

    @app.get("/events")
    def events(since: int = 0) -> list[dict[str, object]]:
        return state.event_log.since(since)

    @app.get("/runs")
    def runs() -> list[dict[str, object]]:
        return state.event_log.runs()

    @app.get("/stream")
    async def stream() -> StreamingResponse:
        queue = state.event_log.subscribe()

        async def events_stream():
            try:
                while True:
                    event = await queue.get()
                    yield f"data: {json.dumps(event)}\n\n"
            finally:
                state.event_log.unsubscribe(queue)

        return StreamingResponse(events_stream(), media_type="text/event-stream")

    @app.post("/run")
    async def run_agent(request: RunRequest, background_tasks: BackgroundTasks) -> dict[str, object]:
        if state.policy is None or not state.confirmed:
            raise HTTPException(status_code=409, detail="A confirmed policy is required before a run.")
        run_id = state.event_log.start_run()
        background_tasks.add_task(
            _execute_agent_run,
            run_id,
            state.agent_runner,
            state.policy,
            request.prompt,
            state.event_log,
            state.sandbox_root,
        )
        return {"accepted": True, "run_id": run_id, "message": "Agent run started."}

    @app.post("/escalation/{event_id}/{resolution}")
    def resolve_escalation(event_id: int, resolution: str) -> dict[str, object]:
        if resolution not in {"approved", "rejected"}:
            raise HTTPException(status_code=422, detail="Resolution must be approved or rejected.")
        claimed = state.event_log.claim_escalation(event_id, resolution)
        if claimed is None:
            raise HTTPException(status_code=409, detail="This escalation is not pending.")
        if resolution == "rejected":
            return {"event_id": event_id, "resolution": "rejected"}
        action, policy = claimed
        verdict = enforce(action, policy, EnforcementContext())
        if verdict.decision != Decision.ESCALATE:
            raise HTTPException(status_code=409, detail="Stored escalation no longer requires approval.")
        result = dispatch_after_approval(action, Sandbox(state.sandbox_root, reset=False))
        return {"event_id": event_id, "resolution": "approved", "result": result}

    return app


async def _run_local_agent(policy: Policy, prompt: str, event_log: EventLog, sandbox_root: Path) -> str:
    """Create a per-run guarded agent context and execute it after policy confirmation."""

    from interlock.agent import build_agent, make_local_context, run_agent

    context = make_local_context(policy, sandbox_root, event_log.db_path)
    agent = build_agent(context)
    return await run_agent(agent, prompt, context)


async def _execute_agent_run(
    run_id: int, runner: AgentRunner, policy: Policy, prompt: str, event_log: EventLog, sandbox_root: Path
) -> None:
    """Run the agent and record a durable terminal state without exposing exception details."""

    try:
        result = await runner(policy, prompt, event_log, sandbox_root)
    except Exception:
        event_log.finish_run(run_id, "failed", "Agent run failed; inspect server logs for details.")
    else:
        event_log.finish_run(run_id, "completed", result)


# The default development server keeps all demo state in a local temporary directory.
app = create_app(EventLog(Path("/tmp/interlock/events.sqlite")))
