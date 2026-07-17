from pathlib import Path
from typing import Awaitable, Callable

from fastapi.testclient import TestClient

from interlock.api.eventlog import EventLog
from interlock.api.main import create_app
from interlock.engine.models import Policy


PolicyCompiler = Callable[[str], Awaitable[Policy]]


async def static_compiler(task: str) -> Policy:
    return Policy(task=task)


def test_policy_requires_confirmation_before_run(tmp_path: Path) -> None:
    client = TestClient(create_app(EventLog(tmp_path / "events.sqlite"), policy_compiler=static_compiler))

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
    client = TestClient(create_app(log, agent_runner=fake_runner, policy_compiler=static_compiler))
    drafted = client.post("/policy", json={"task": "inspect sessions"})
    client.put("/policy", json={**drafted.json(), "confirmed": True})

    response = client.post("/run", json={"prompt": "inspect the schema"})

    assert response.status_code == 200
    assert response.json() == {"accepted": True, "run_id": 1, "message": "Agent run started."}
    assert calls == [("inspect sessions", "inspect the schema", tmp_path / "sandbox")]
    assert client.get("/runs").json() == [{"id": 1, "status": "completed", "detail": "Agent run completed."}]


def test_failed_agent_run_is_recorded_without_exposing_exception(tmp_path: Path) -> None:
    async def failing_runner(_policy: Policy, _prompt: str, _log: EventLog, _root: Path) -> str:
        raise RuntimeError("secret upstream failure")

    log = EventLog(tmp_path / "events.sqlite")
    client = TestClient(create_app(log, agent_runner=failing_runner, policy_compiler=static_compiler))
    drafted = client.post("/policy", json={"task": "inspect sessions"})
    client.put("/policy", json={**drafted.json(), "confirmed": True})

    response = client.post("/run", json={"prompt": "inspect the schema"})

    assert response.status_code == 200
    assert client.get("/runs").json() == [
        {"id": 1, "status": "failed", "detail": "Agent run failed; inspect server logs for details."}
    ]


def test_policy_draft_uses_injected_compiler(tmp_path: Path) -> None:
    async def compiler(task: str) -> Policy:
        return Policy(task=task, allowed_tools={"inspect"})

    client = TestClient(create_app(EventLog(tmp_path / "events.sqlite"), policy_compiler=compiler))

    response = client.post("/policy", json={"task": "inspect the ledger"})

    assert response.status_code == 200
    assert response.json()["allowed_tools"] == ["inspect"]


def test_local_dashboard_origin_is_allowed_to_call_api(tmp_path: Path) -> None:
    client = TestClient(create_app(EventLog(tmp_path / "events.sqlite"), policy_compiler=static_compiler))

    response = client.options(
        "/policy",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"


def test_health_endpoint_reports_api_ready(tmp_path: Path) -> None:
    client = TestClient(create_app(EventLog(tmp_path / "events.sqlite"), policy_compiler=static_compiler))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_confirmed_safety_demo_emits_allowed_and_halted_verdicts(tmp_path: Path) -> None:
    async def compiler(task: str) -> Policy:
        return Policy(
            task=task,
            allowed_tools={"inspect"},
            forbidden_patterns=["DROP TABLE"],
        )

    client = TestClient(create_app(EventLog(tmp_path / "events.sqlite"), policy_compiler=compiler))
    drafted = client.post("/policy", json={"task": "inspect sessions"})
    client.put("/policy", json={**drafted.json(), "confirmed": True})

    response = client.post("/demo")

    assert response.status_code == 200
    assert response.json()["allowed"]["rows"] == [
        {"name": "ledger"}, {"name": "sessions"}, {"name": "users"}
    ]
    assert response.json()["blocked"]["blocked"] is True
    assert [event["decision"] for event in client.get("/events").json()] == ["allow", "halt"]
    assert client.get("/runs").json() == [{"id": 1, "status": "completed", "detail": "Safety demo completed: allowed read and blocked destructive action."}]
