from pathlib import Path

from interlock.api.eventlog import EventLog
from interlock.engine.models import (
    DbAction,
    DbArgs,
    Decision,
    Reversibility,
    Verdict,
    Policy,
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


def test_escalation_action_and_policy_are_persisted_and_claimed_once(tmp_path: Path) -> None:
    log = EventLog(tmp_path / "events.sqlite")
    action = DbAction(args=DbArgs(sql="DELETE FROM sessions WHERE id = 1"))
    policy = Policy(
        task="clean sessions",
        allowed_tools={"db"},
        allowed_db_ops={"DELETE"},
        allowed_db_tables={"sessions"},
    )
    event_id = log.emit(
        Verdict(
            decision=Decision.ESCALATE,
            reversibility=Reversibility.IRREVERSIBLE,
            reason="requires approval",
            matched_rule="irreversible_in_scope",
            action=action,
        )
    )
    log.record_escalation(event_id, action, policy)

    claimed = log.claim_escalation(event_id, "approved")

    assert claimed == (action, policy)
    assert log.claim_escalation(event_id, "approved") is None


def test_run_lifecycle_is_durable(tmp_path: Path) -> None:
    log = EventLog(tmp_path / "events.sqlite")

    run_id = log.start_run()
    log.finish_run(run_id, "completed", "inspection complete")

    assert log.runs() == [{"id": run_id, "status": "completed", "detail": "inspection complete"}]


def test_unsubscribed_sse_queue_does_not_receive_future_events(tmp_path: Path) -> None:
    log = EventLog(tmp_path / "events.sqlite")
    queue = log.subscribe()
    log.unsubscribe(queue)
    verdict = Verdict(
        decision=Decision.ALLOW,
        reversibility=Reversibility.REVERSIBLE,
        reason="safe read",
        matched_rule="reversible",
        action=DbAction(args=DbArgs(sql="SELECT * FROM sessions")),
    )

    log.emit(verdict)

    assert queue.empty()
