from pydantic import ValidationError
import pytest

from interlock.engine.models import (
    DbArgs,
    DbAction,
    EnforcementContext,
    FsWriteAction,
    Policy,
    TransferAction,
)


def test_policy_defaults_are_failsafe() -> None:
    policy = Policy(task="clean sessions")

    assert policy.allowed_tools == set()
    assert policy.allowed_roots == []
    assert policy.allowed_db_ops == set()
    assert policy.allowed_db_tables == set()
    assert policy.spend_cap_cents == 0


def test_typed_actions_round_trip() -> None:
    action = DbAction(args=DbArgs(sql="SELECT * FROM sessions"))

    assert action.tool == "db"
    assert action.args.sql == "SELECT * FROM sessions"


def test_action_payloads_reject_the_wrong_shape() -> None:
    with pytest.raises(ValidationError):
        TransferAction(args={"cents": 100})

    with pytest.raises(ValidationError):
        FsWriteAction(args={"path": "/tmp/demo/a.txt"})


def test_enforcement_context_starts_with_no_spend() -> None:
    assert EnforcementContext().spent_cents == 0
