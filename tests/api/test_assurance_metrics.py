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


def test_assurance_metrics_record_lifecycle_and_evidence_outcomes_without_payloads(tmp_path) -> None:
    client = TestClient(create_app(EventLog(tmp_path / "events.sqlite")))
    manifest = {"release_id": "candidate", "source": "test", "components": {"policy": "a" * 64}, "authority": {}}
    created = client.post("/assurance/candidates", json={"title": "Metric case", "summary": "No payload retained.", "source": "test", "owner": "qa"})
    client.post(f"/assurance/candidates/{created.json()['case_id']}/approved", json={"reviewer": "reviewer"})
    report = client.post("/assurance/report", json={"baseline": manifest, "candidate": manifest, "replays": [{"case_id": 1, "passed": True}]})
    client.post("/assurance/verify", json=report.json())

    counters = client.get("/assurance/metrics").json()["counters"]

    assert counters == {"candidate:approved": 1, "candidate:created": 1, "report:pass": 1, "report:verified": 1}
