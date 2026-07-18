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
from interlock.engine.models import DbAction, DbArgs, Decision, EnforcementContext, InspectAction, InspectArgs, Policy
from interlock.interceptor import dispatch_after_approval, guarded_call
from interlock.intent import compile_policy_with_openai
from interlock.engine.simulator import (
    SimulationResult,
    SimulationStep,
    developer_agent_trace,
    simulate,
)
from interlock.tools.sandbox import Sandbox


AgentRunner = Callable[[Policy, str, EventLog, Path], Awaitable[str]]
PolicyCompiler = Callable[[str], Awaitable[Policy]]


class TaskRequest(BaseModel):
    task: str


class RunRequest(BaseModel):
    prompt: str


class PolicyUpdate(Policy):
    confirmed: bool = False


class SimulationRequest(BaseModel):
    """A proposed policy plus labeled trace to replay without side effects."""

    policy: Policy
    steps: list[SimulationStep]


class GuardrailRequest(BaseModel):
    """A human-reviewable pattern learned from a verified incident or simulation."""

    name: str
    pattern: str
    reason: str


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

    @app.post("/simulate", response_model=SimulationResult)
    def simulate_policy(request: SimulationRequest) -> SimulationResult:
        """Evaluate a candidate policy against a trace without emitting or dispatching actions."""

        return simulate(_with_global_guardrails(request.policy, state.event_log), request.steps)

    @app.post("/simulate/developer-trace", response_model=SimulationResult)
    def simulate_developer_trace() -> SimulationResult:
        """Replay the built-in DevOps trace against the currently drafted policy."""

        if state.policy is None:
            raise HTTPException(status_code=409, detail="Draft a policy before simulating it.")
        return simulate(_with_global_guardrails(state.policy, state.event_log), developer_agent_trace())

    @app.get("/guardrails")
    def guardrails() -> list[dict[str, object]]:
        return state.event_log.guardrails()

    @app.post("/guardrails")
    def create_guardrail(request: GuardrailRequest) -> dict[str, object]:
        return state.event_log.create_guardrail(request.name, request.pattern, request.reason)

    @app.post("/guardrails/{guardrail_id}/{resolution}")
    def resolve_guardrail(guardrail_id: int, resolution: str) -> dict[str, object]:
        if resolution not in {"approved", "rejected"}:
            raise HTTPException(status_code=422, detail="Resolution must be approved or rejected.")
        guardrail = state.event_log.resolve_guardrail(guardrail_id, resolution)
        if guardrail is None:
            raise HTTPException(status_code=409, detail="This guardrail is not pending.")
        return guardrail

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
        effective_policy = _with_global_guardrails(state.policy, state.event_log)
        run_id = state.event_log.start_run()
        background_tasks.add_task(
            _execute_agent_run,
            run_id,
            state.agent_runner,
            effective_policy,
            request.prompt,
            state.event_log,
            state.sandbox_root,
        )
        return {"accepted": True, "run_id": run_id, "message": "Agent run started."}

    @app.post("/demo")
    async def run_safety_demo() -> dict[str, object]:
        """Run a real, local allow/halt sequence through the enforcement boundary.

        This is deliberately model-free so a live product demo never depends on an
        upstream model moderation response. Both actions still use the exact same
        interceptor and sandbox dispatch path as the GPT-powered agent.
        """

        if state.policy is None or not state.confirmed:
            raise HTTPException(status_code=409, detail="A confirmed policy is required before a demo.")
        run_id = state.event_log.start_run()
        policy = _with_global_guardrails(state.policy, state.event_log)
        sandbox = Sandbox(state.sandbox_root)
        try:
            allowed = await guarded_call(
                InspectAction(args=InspectArgs(resource="db_schema")),
                policy,
                EnforcementContext(),
                state.event_log,
                sandbox,
            )
            blocked = await guarded_call(
                DbAction(args=DbArgs(sql="DROP TABLE users")),
                policy,
                EnforcementContext(),
                state.event_log,
                sandbox,
            )
        except Exception:
            state.event_log.finish_run(run_id, "failed", "Safety demo failed; inspect server logs for details.")
            raise
        state.event_log.finish_run(run_id, "completed", "Safety demo completed: allowed read and blocked destructive action.")
        return {"run_id": run_id, "allowed": allowed, "blocked": blocked}

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


def _with_global_guardrails(policy: Policy, event_log: EventLog) -> Policy:
    """Compose approved organizational patterns with a run's human-confirmed policy."""

    patterns = list(dict.fromkeys([*policy.forbidden_patterns, *event_log.active_forbidden_patterns()]))
    return policy.model_copy(update={"forbidden_patterns": patterns})


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
        await runner(policy, prompt, event_log, sandbox_root)
    except Exception:
        event_log.finish_run(run_id, "failed", "Agent run failed; inspect server logs for details.")
    else:
        event_log.finish_run(run_id, "completed", "Agent run completed.")


# The default development server keeps all demo state in a local temporary directory.
app = create_app(EventLog(Path("/tmp/interlock/events.sqlite")))
