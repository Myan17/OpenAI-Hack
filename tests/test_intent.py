from interlock.engine.models import Policy
from interlock.intent import compile_policy


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
