from pathlib import Path

from interlock.api.eventlog import EventLog
from interlock.engine.models import (
    DbAction,
    DbArgs,
    Decision,
    Reversibility,
    Verdict,
)


def test_append_and_since_return_audit_row(tmp_path: Path) -> None:
    log = EventLog(tmp_path / "events.sqlite")
    verdict = Verdict(
        decision=Decision.ALLOW,
        reversibility=Reversibility.REVERSIBLE,
        reason="safe read",
        matched_rule="reversible",
        action=DbAction(args=DbArgs(sql="SELECT * FROM sessions")),
    )

    event_id = log.emit(verdict)
    rows = log.since(0)

    assert event_id == 1
    assert rows[0]["id"] == 1
    assert rows[0]["tool"] == "db"
    assert rows[0]["decision"] == "allow"
