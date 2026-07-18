"""Tests for assurance rollout controls that leave runtime enforcement available."""

from fastapi.testclient import TestClient

from interlock.api.eventlog import EventLog
from interlock.api.main import create_app


def test_disabling_assurance_does_not_disable_existing_runtime_health(tmp_path) -> None:
    client = TestClient(create_app(EventLog(tmp_path / "events.sqlite"), assurance_enabled=False))

    health = client.get("/health")
    assurance_health = client.get("/assurance/health")
    manifest = {
        "release_id": "candidate", "source": "test", "components": {"policy": "a" * 64}, "authority": {},
    }
    diff = client.post("/assurance/diff", json={"baseline": manifest, "candidate": manifest})

    assert health.json() == {"status": "ok"}
    assert assurance_health.json() == {"status": "disabled", "mode": "report_only"}
    assert diff.status_code == 503


def test_enabled_assurance_health_reports_advisory_mode(tmp_path) -> None:
    client = TestClient(create_app(EventLog(tmp_path / "events.sqlite")))

    response = client.get("/assurance/health")

    assert response.json() == {"status": "ok", "mode": "report_only"}
