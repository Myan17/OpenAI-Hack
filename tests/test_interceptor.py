from dataclasses import dataclass, field
from pathlib import Path

import pytest

from interlock.engine.models import (
    DbAction,
    DbArgs,
    Decision,
    EnforcementContext,
    GitHubAction,
    GitHubArgs,
    Policy,
    TransferAction,
    TransferArgs,
    Verdict,
)
from interlock.interceptor import guarded_call
from interlock.tools.sandbox import Sandbox


@dataclass
class RecordingSink:
    verdicts: list[Verdict] = field(default_factory=list)

    def emit(self, verdict: Verdict) -> int:
        self.verdicts.append(verdict)
        return len(self.verdicts)


def policy() -> Policy:
    return Policy(
        task="inspect sessions",
        allowed_tools={"db", "transfer"},
        allowed_db_ops={"SELECT", "DELETE"},
        allowed_db_tables={"sessions"},
        spend_cap_cents=500,
    )


@pytest.mark.asyncio
async def test_halted_action_does_not_dispatch(tmp_path: Path) -> None:
    sandbox = Sandbox(tmp_path / "demo", opening_balance_cents=1_000)
    sink = RecordingSink()

    result = await guarded_call(
        TransferAction(args=TransferArgs(cents=600, to="vendor")),
        policy(),
        EnforcementContext(),
        sink,
        sandbox,
    )

    assert result["blocked"] is True
    assert sink.verdicts[0].decision == Decision.HALT
    assert sandbox.inspect("ledger")["balance_cents"] == 1_000


@pytest.mark.asyncio
async def test_allowed_action_dispatches_and_emits_once(tmp_path: Path) -> None:
    sandbox = Sandbox(tmp_path / "demo")
    sink = RecordingSink()

    result = await guarded_call(
        DbAction(args=DbArgs(sql="SELECT count(*) AS count FROM sessions")),
        policy(),
        EnforcementContext(),
        sink,
        sandbox,
    )

    assert result["rows"][0]["count"] == 2
    assert len(sink.verdicts) == 1
    assert sink.verdicts[0].decision == Decision.ALLOW


@pytest.mark.asyncio
async def test_allowed_github_read_dispatches_only_to_the_local_adapter(tmp_path: Path) -> None:
    sandbox = Sandbox(tmp_path / "demo")
    sink = RecordingSink()
    github_policy = Policy(
        task="read issue",
        allowed_tools={"github"},
        allowed_github_operations={"read_issue"},
        allowed_github_repositories={"acme/api"},
    )

    result = await guarded_call(
        GitHubAction(args=GitHubArgs(operation="read_issue", repository="acme/api", issue_number=42)),
        github_policy,
        EnforcementContext(),
        sink,
        sandbox,
    )

    assert result == {"operation": "read_issue", "repository": "acme/api", "issue_number": 42}
    assert sink.verdicts[0].decision == Decision.ALLOW
