import pytest
import json

from interlock.engine.models import Policy
from interlock.intent import PolicyDraft, compile_policy, compile_policy_with_openai


class GoodClient:
    def compile(self, _task: str) -> dict[str, object]:
        return {
            "task": "inspect sessions",
            "allowed_tools": ["db"],
            "allowed_roots": [],
            "allowed_db_ops": ["SELECT"],
            "allowed_db_tables": ["sessions"],
            "spend_cap_cents": 0,
            "forbidden_patterns": [r"DROP\s+TABLE"],
        }


class BadClient:
    def compile(self, _task: str) -> object:
        return {"not": "a policy"}


def test_compiler_validates_structured_policy() -> None:
    policy = compile_policy("inspect sessions", GoodClient())
    assert policy.allowed_tools == {"db"}


def test_compiler_falls_back_to_deny_all() -> None:
    policy = compile_policy("inspect sessions", BadClient())
    assert policy == Policy(task="inspect sessions")


def test_model_policy_schema_avoids_unique_items() -> None:
    schema = PolicyDraft.model_json_schema()
    assert "uniqueItems" not in json.dumps(schema["properties"])


@pytest.mark.asyncio
async def test_openai_compiler_validates_runner_output_and_preserves_requested_task() -> None:
    async def runner(_task: str) -> object:
        return {"task": "model changed this", "allowed_tools": ["inspect"]}

    policy = await compile_policy_with_openai("inspect the ledger", runner=runner)

    assert policy == Policy(task="inspect the ledger", allowed_tools={"inspect"})


@pytest.mark.asyncio
async def test_openai_compiler_fails_closed_when_runner_errors() -> None:
    async def failing_runner(_task: str) -> object:
        raise RuntimeError("network unavailable")

    assert await compile_policy_with_openai("inspect sessions", runner=failing_runner) == Policy(task="inspect sessions")
