"""Minimal HTTP surface for policy confirmation and the audit feed."""

from dataclasses import dataclass

import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from interlock.api.eventlog import EventLog
from interlock.engine.models import Policy


class TaskRequest(BaseModel):
    task: str


class RunRequest(BaseModel):
    prompt: str


class PolicyUpdate(Policy):
    confirmed: bool = False


@dataclass
class AppState:
    event_log: EventLog
    policy: Policy | None = None
    confirmed: bool = False


def create_app(event_log: EventLog) -> FastAPI:
    """Create an app with injected persistence, making HTTP tests isolated."""

    app = FastAPI(title="Interlock")
    state = AppState(event_log=event_log)

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
    def run_agent(_request: RunRequest) -> dict[str, object]:
        if state.policy is None or not state.confirmed:
            raise HTTPException(status_code=409, detail="A confirmed policy is required before a run.")
        return {"accepted": True, "message": "Agent execution will be wired in the next phase."}

    return app
