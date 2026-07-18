"""Tests for the assurance metrics API without sensitive trace capture."""

from fastapi.testclient import TestClient

from interlock.api.eventlog import EventLog
from interlock.api.main import create_app


def test_assurance_metrics_expose_aggregate_diff_activity_only(tmp_path) -> None:
    client = TestClient(create_app(EventLog(tmp_path / "events.sqlite")))
    manifest = {
        "release_id": "candidate", "source": "test", "components": {"policy": "a" * 64}, "authority": {},
    }

    client.post("/assurance/diff", json={"baseline": manifest, "candidate": manifest})
    response = client.get("/assurance/metrics")

    assert response.json()["counters"] == {"authority_diff": 1}
