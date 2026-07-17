from interlock.engine.catalog import classify
from interlock.engine.models import (
    DbAction,
    DbArgs,
    FsWriteAction,
    FsWriteArgs,
    InspectAction,
    InspectArgs,
    Reversibility,
    TransferAction,
    TransferArgs,
)


def test_recognized_read_actions_are_reversible() -> None:
    assert (
        classify(DbAction(args=DbArgs(sql="SELECT * FROM sessions")))
        == Reversibility.REVERSIBLE
    )
    assert (
        classify(InspectAction(args=InspectArgs(resource="db_schema")))
        == Reversibility.REVERSIBLE
    )


def test_known_mutations_are_irreversible() -> None:
    assert (
        classify(DbAction(args=DbArgs(sql="DROP TABLE users")))
        == Reversibility.IRREVERSIBLE
    )
    assert (
        classify(TransferAction(args=TransferArgs(cents=1, to="vendor")))
        == Reversibility.IRREVERSIBLE
    )
    assert (
        classify(FsWriteAction(args=FsWriteArgs(path="/tmp/demo/a.txt", content="x")))
        == Reversibility.IRREVERSIBLE
    )


def test_ambiguous_sql_fails_closed_as_unknown() -> None:
    assert (
        classify(DbAction(args=DbArgs(sql="SELECT * FROM sessions; DROP TABLE users")))
        == Reversibility.UNKNOWN
    )
    assert (
        classify(DbAction(args=DbArgs(sql="WITH rows AS (SELECT 1) SELECT * FROM rows")))
        == Reversibility.UNKNOWN
    )
