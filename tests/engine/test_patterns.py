from interlock.engine.models import DbAction, DbArgs, TransferAction, TransferArgs
from interlock.engine.patterns import matches_forbidden


def test_matches_forbidden_sql_case_insensitively() -> None:
    action = DbAction(args=DbArgs(sql="drop table users"))

    assert matches_forbidden(action, [r"DROP\s+TABLE"]) == r"DROP\s+TABLE"


def test_stable_serialization_matches_typed_transfer_fields() -> None:
    action = TransferAction(args=TransferArgs(cents=500_000, to="attacker"))

    assert matches_forbidden(action, [r'"cents":500000']) == r'"cents":500000'


def test_no_match_returns_none() -> None:
    action = DbAction(args=DbArgs(sql="SELECT * FROM sessions"))

    assert matches_forbidden(action, [r"DROP\s+TABLE"]) is None
