"""Single pre-execution enforcement boundary for local sandbox tools."""

from typing import Protocol

from interlock.engine.enforcer import enforce
from interlock.engine.models import (
    DbAction,
    EnforcementContext,
    FsWriteAction,
    InspectAction,
    Policy,
    ProposedAction,
    TransferAction,
    Verdict,
)
from interlock.tools.sandbox import Sandbox


class EventSink(Protocol):
    """Records a decision and returns its stable event identifier."""

    def emit(self, verdict: Verdict) -> int: ...


async def guarded_call(
    action: ProposedAction,
    policy: Policy,
    context: EnforcementContext,
    sink: EventSink,
    sandbox: Sandbox,
) -> dict[str, object]:
    """Enforce, record, then dispatch only an allowed sandbox action."""

    verdict = enforce(action, policy, context)
    event_id = sink.emit(verdict)
    if verdict.decision.value == "halt":
        return {"blocked": True, "reason": verdict.reason, "event_id": event_id}
    if verdict.decision.value == "escalate":
        return {"blocked": True, "escalated": True, "reason": verdict.reason, "event_id": event_id}
    return _dispatch(action, sandbox)


def _dispatch(action: ProposedAction, sandbox: Sandbox) -> dict[str, object]:
    """Dispatch only after an ALLOW verdict; action types select the contained tool."""

    if isinstance(action, DbAction):
        return sandbox.run_db(action.args.sql)
    if isinstance(action, TransferAction):
        return sandbox.transfer(action.args.cents, action.args.to)
    if isinstance(action, FsWriteAction):
        return sandbox.fs_write(action.args.path, action.args.content)
    if isinstance(action, InspectAction):
        return sandbox.inspect(action.args.resource)
    raise TypeError("unsupported typed action")
