import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from interlock.api.eventlog import EventLog
from interlock.api.main import create_app
from interlock.engine.models import DbAction, DbArgs, EnforcementContext, Policy
from interlock.interceptor import guarded_call
from interlock.tools.sandbox import Sandbox


def test_escalated_action_waits_for_one_persisted_approval(tmp_path: Path) -> None:
    log = EventLog(tmp_path / "events.sqlite")
    client = TestClient(create_app(log))
    root = tmp_path / "sandbox"
    sandbox = Sandbox(root)
    policy = Policy(
        task="clean sessions",
        allowed_tools={"db"},
        allowed_db_ops={"DELETE"},
        allowed_db_tables={"sessions"},
    )
    action = DbAction(args=DbArgs(sql="DELETE FROM sessions WHERE id = 1"))

    blocked = asyncio.run(guarded_call(action, policy, EnforcementContext(), log, sandbox))

    assert blocked["escalated"] is True
    assert sandbox.run_db("SELECT count(*) AS count FROM sessions")["rows"][0]["count"] == 2
    approved = client.post(f"/escalation/{blocked['event_id']}/approved")

    assert approved.status_code == 200
    assert approved.json()["resolution"] == "approved"
    assert Sandbox(root, reset=False).run_db("SELECT count(*) AS count FROM sessions")["rows"][0]["count"] == 1
    assert client.post(f"/escalation/{blocked['event_id']}/approved").status_code == 409
