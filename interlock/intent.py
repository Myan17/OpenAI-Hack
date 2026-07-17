"""One-shot GPT policy drafting with a fail-closed fallback."""

from collections.abc import Awaitable, Callable
from typing import Protocol

from pydantic import BaseModel, Field, ValidationError

from interlock.engine.models import Policy
from interlock.tracing import trace_policy


class PolicyCompilerClient(Protocol):
    def compile(self, task: str) -> object: ...


class PolicyDraft(BaseModel):
    """Wire-safe structured-output contract for the policy drafting model.

    The Responses structured-output API rejects JSON Schema's ``uniqueItems``.
    ``Policy`` intentionally uses sets for deterministic membership checks, so the
    model-facing contract uses lists and the boundary converts it back to Policy.
    """

    task: str
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_roots: list[str] = Field(default_factory=list)
    allowed_db_ops: list[str] = Field(default_factory=list)
    allowed_db_tables: list[str] = Field(default_factory=list)
    spend_cap_cents: int = 0
    forbidden_patterns: list[str] = Field(default_factory=list)


def compile_policy(task: str, client: PolicyCompilerClient) -> Policy:
    """Compile one structured policy; malformed model output yields deny-all."""

    try:
        return Policy.model_validate(client.compile(task))
    except (ValidationError, TypeError, ValueError):
        return Policy(task=task)


PolicyRunner = Callable[[str], Awaitable[object]]


async def compile_policy_with_openai(task: str, runner: PolicyRunner | None = None) -> Policy:
    """Draft one policy with GPT-5.6, retaining a deny-all policy on every failure.

    This function is intentionally outside ``interlock.engine``.  The returned policy must be
    explicitly confirmed before it can authorize an agent run.
    """

    try:
        raw_policy = await (runner or _run_openai_compiler)(task)
        draft = PolicyDraft.model_validate(raw_policy)
        policy = Policy.model_validate(draft.model_dump() | {"task": task})
    except (Exception,):
        policy = Policy(task=task)
    trace_policy(task, policy)
    return policy


async def _run_openai_compiler(task: str) -> object:
    """Use the Agents SDK structured-output seam for a single offline policy draft."""

    from agents import Agent, Runner

    compiler = Agent(
        name="Interlock Policy Compiler",
        model="gpt-5.6",
        output_type=PolicyDraft,
        instructions=(
            "Translate the user's task into the least-privilege Interlock Policy schema. "
            "Only name these local tools: db, inspect, fs_write, transfer. "
            "Use an empty allowlist when the task is ambiguous. "
            "Never authorize DROP TABLE, unknown database tables, arbitrary paths, or money "
            "movement unless the task explicitly requires it."
        ),
    )
    result = await Runner.run(compiler, task)
    return result.final_output
