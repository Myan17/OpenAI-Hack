"""Optional LangFuse observability outside the deterministic enforcement package."""

import os
from typing import Protocol

from interlock.engine.models import Policy, Verdict


class EventClient(Protocol):
    """Small adapter surface used by the optional LangFuse SDK client."""

    def create_event(self, *, name: str, input: object, output: object, metadata: object) -> object: ...


def trace_verdict(verdict: Verdict, client: EventClient | None = None) -> bool:
    """Emit a verdict trace only when LangFuse credentials explicitly enable tracing."""

    if not _enabled():
        return False
    try:
        active_client = client or _langfuse_client()
        active_client.create_event(
            name="interlock.verdict",
            input=verdict.action.model_dump(mode="json"),
            output={"decision": verdict.decision.value, "rule": verdict.matched_rule},
            metadata={"reversibility": verdict.reversibility.value},
        )
        return True
    except Exception:
        return False


def trace_policy(task: str, policy: Policy, client: EventClient | None = None) -> bool:
    """Record the one-shot policy draft when optional tracing is enabled."""

    if not _enabled():
        return False
    try:
        active_client = client or _langfuse_client()
        active_client.create_event(
            name="interlock.policy_draft",
            input={"task": task},
            output=policy.model_dump(mode="json"),
            metadata={"allowed_tools": sorted(policy.allowed_tools)},
        )
        return True
    except Exception:
        return False


def _enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def _langfuse_client() -> EventClient:
    from langfuse import get_client

    return get_client()
