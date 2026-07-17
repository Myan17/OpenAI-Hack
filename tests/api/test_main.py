from pathlib import Path

from fastapi.testclient import TestClient

from interlock.api.eventlog import EventLog
from interlock.api.main import create_app
from interlock.engine.models import Policy


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


def test_confirmed_run_launches_injected_agent_runner(tmp_path: Path) -> None:
    calls: list[tuple[str, str, Path]] = []

    async def fake_runner(policy: Policy, prompt: str, _log: EventLog, root: Path) -> str:
        calls.append((policy.task, prompt, root))
        return "completed"

    log = EventLog(tmp_path / "events.sqlite")
    client = TestClient(create_app(log, agent_runner=fake_runner))
    drafted = client.post("/policy", json={"task": "inspect sessions"})
    client.put("/policy", json={**drafted.json(), "confirmed": True})

    response = client.post("/run", json={"prompt": "inspect the schema"})

    assert response.status_code == 200
    assert response.json() == {"accepted": True, "message": "Agent run started."}
    assert calls == [("inspect sessions", "inspect the schema", tmp_path / "sandbox")]
