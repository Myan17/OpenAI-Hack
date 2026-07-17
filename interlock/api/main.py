"""Minimal HTTP surface for policy confirmation and the audit feed."""

from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

import json

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from interlock.api.eventlog import EventLog
from interlock.engine.models import Policy


AgentRunner = Callable[[Policy, str, EventLog, Path], Awaitable[str]]


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
    policy: Policy | None = None
    confirmed: bool = False


def create_app(event_log: EventLog, agent_runner: AgentRunner | None = None) -> FastAPI:
    """Create an app with injected persistence, making HTTP tests isolated."""

    app = FastAPI(title="Interlock")
    state = AppState(
        event_log=event_log,
        sandbox_root=event_log.db_path.parent / "sandbox",
        agent_runner=agent_runner or _run_local_agent,
    )

    @app.post("/policy", response_model=Policy)
    def draft_policy(request: TaskRequest) -> Policy:
        state.policy = Policy(task=request.task)
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

    @app.get("/stream")
    async def stream() -> StreamingResponse:
        queue = state.event_log.subscribe()

        async def events_stream():
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"

        return StreamingResponse(events_stream(), media_type="text/event-stream")

    @app.post("/run")
    async def run_agent(request: RunRequest, background_tasks: BackgroundTasks) -> dict[str, object]:
        if state.policy is None or not state.confirmed:
            raise HTTPException(status_code=409, detail="A confirmed policy is required before a run.")
        background_tasks.add_task(
            state.agent_runner,
            state.policy,
            request.prompt,
            state.event_log,
            state.sandbox_root,
        )
        return {"accepted": True, "message": "Agent run started."}

    return app


async def _run_local_agent(policy: Policy, prompt: str, event_log: EventLog, sandbox_root: Path) -> str:
    """Create a per-run guarded agent context and execute it after policy confirmation."""

    from interlock.agent import build_agent, make_local_context, run_agent

    context = make_local_context(policy, sandbox_root, event_log.db_path)
    agent = build_agent(context)
    return await run_agent(agent, prompt, context)
