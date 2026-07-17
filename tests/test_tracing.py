from interlock.engine.models import DbAction, DbArgs, Decision, Policy, Reversibility, Verdict
from interlock.tracing import trace_policy, trace_verdict


class FakeClient:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def create_event(self, **event: object) -> object:
        self.events.append(event)
        return object()


def test_verdict_tracing_is_disabled_without_credentials(monkeypatch) -> None:
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    verdict = Verdict(decision=Decision.ALLOW, reversibility=Reversibility.REVERSIBLE, reason="ok", matched_rule="reversible", action=DbAction(args=DbArgs(sql="SELECT * FROM sessions")))

    assert trace_verdict(verdict, FakeClient()) is False


def test_verdict_tracing_records_metadata_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    client = FakeClient()
    verdict = Verdict(decision=Decision.HALT, reversibility=Reversibility.UNKNOWN, reason="blocked", matched_rule="default_deny", action=DbAction(args=DbArgs(sql="DROP TABLE users")))

    assert trace_verdict(verdict, client) is True
    assert client.events[0]["name"] == "interlock.verdict"


def test_policy_draft_tracing_records_only_policy_metadata(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    client = FakeClient()

    assert trace_policy("inspect sessions", Policy(task="inspect sessions"), client) is True
    assert client.events[0]["name"] == "interlock.policy_draft"
