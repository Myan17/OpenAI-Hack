"""One-shot intent compilation with a fail-closed fallback."""

from typing import Protocol

from pydantic import ValidationError

from interlock.engine.models import Policy


class PolicyCompilerClient(Protocol):
    def compile(self, task: str) -> object: ...


def compile_policy(task: str, client: PolicyCompilerClient) -> Policy:
    """Compile one structured policy; malformed model output yields deny-all."""

    try:
        return Policy.model_validate(client.compile(task))
    except (ValidationError, TypeError, ValueError):
        return Policy(task=task)
