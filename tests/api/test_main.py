from pathlib import Path

from fastapi.testclient import TestClient

from interlock.api.eventlog import EventLog
from interlock.api.main import create_app


def test_policy_requires_confirmation_before_run(tmp_path: Path) -> None:
    client = TestClient(create_app(EventLog(tmp_path / "events.sqlite")))

    drafted = client.post("/policy", json={"task": "inspect sessions"})
    rejected_run = client.post("/run", json={"prompt": "inspect sessions"})
    confirmed = client.put("/policy", json={**drafted.json(), "confirmed": True})

    assert drafted.status_code == 200
    assert drafted.json()["allowed_tools"] == []
    assert rejected_run.status_code == 409
    assert confirmed.status_code == 200
    assert client.get("/events?since=0").json() == []
