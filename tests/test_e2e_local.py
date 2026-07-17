from dataclasses import dataclass, field
from pathlib import Path

import pytest

from interlock.engine.models import (
    DbAction,
    DbArgs,
    EnforcementContext,
    Policy,
    TransferAction,
    TransferArgs,
    Verdict,
)
from interlock.interceptor import guarded_call
from interlock.tools.sandbox import Sandbox


@dataclass
class Sink:
    verdicts: list[Verdict] = field(default_factory=list)

    def emit(self, verdict: Verdict) -> int:
        self.verdicts.append(verdict)
        return len(self.verdicts)


@pytest.mark.asyncio
async def test_local_sequence_preserves_blocked_database_and_ledger_state(tmp_path: Path) -> None:
    sandbox = Sandbox(tmp_path / "demo", opening_balance_cents=1_000)
    sink = Sink()
    policy = Policy(
        task="clean stale sessions",
        allowed_tools={"db", "transfer"},
        allowed_db_ops={"SELECT", "DELETE"},
        allowed_db_tables={"sessions"},
        spend_cap_cents=100,
        forbidden_patterns=[r"DROP\s+TABLE"],
    )

    allowed = await guarded_call(
        DbAction(args=DbArgs(sql="SELECT count(*) AS count FROM sessions")),
        policy,
        EnforcementContext(),
        sink,
        sandbox,
    )
    blocked_drop = await guarded_call(
        DbAction(args=DbArgs(sql="DROP TABLE users")),
        policy,
        EnforcementContext(),
        sink,
        sandbox,
    )
    blocked_transfer = await guarded_call(
        TransferAction(args=TransferArgs(cents=500, to="attacker")),
        policy,
        EnforcementContext(),
        sink,
        sandbox,
    )

    assert allowed["rows"][0]["count"] == 2
    assert blocked_drop["blocked"] is True
    assert blocked_transfer["blocked"] is True
    assert sandbox.run_db("SELECT count(*) AS count FROM users")["rows"][0]["count"] == 2
    assert sandbox.inspect("ledger")["balance_cents"] == 1_000
    assert [verdict.decision.value for verdict in sink.verdicts] == ["allow", "halt", "halt"]
