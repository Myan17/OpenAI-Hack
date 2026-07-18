"""Contract tests for additive, report-only assurance API routes."""

from pathlib import Path

from fastapi.testclient import TestClient

from interlock.api.eventlog import EventLog
from interlock.api.main import create_app


def _manifest(release_id: str, tools: list[str]) -> dict[str, object]:
    return {
        "release_id": release_id,
        "source": "api-test",
        "components": {"policy": ("a" if release_id == "baseline" else "b") * 64},
        "authority": {"tools": tools},
    }


def test_assurance_diff_reports_authority_expansion_without_affecting_existing_routes(tmp_path: Path) -> None:
    client = TestClient(create_app(EventLog(tmp_path / "events.sqlite")))

    response = client.post(
        "/assurance/diff",
        json={"baseline": _manifest("baseline", ["inspect"]), "candidate": _manifest("candidate", ["inspect", "db"])},
    )

    assert response.status_code == 200
    assert response.json()["added_tools"] == ["db"]
    assert response.json()["has_expansion"] is True
    assert client.get("/health").json() == {"status": "ok"}


def test_assurance_candidate_requires_review_before_it_is_active(tmp_path: Path) -> None:
    client = TestClient(create_app(EventLog(tmp_path / "events.sqlite")))

    created = client.post(
        "/assurance/candidates",
        json={
            "title": "Block destructive migration",
            "summary": "A destructive migration requires escalation.",
            "source": "event:42",
            "owner": "qa@example.test",
        },
    )
    active_before = client.get("/assurance/candidates?active_only=true")
    reviewed = client.post(
        f"/assurance/candidates/{created.json()['case_id']}/approved",
        json={"reviewer": "reviewer@example.test"},
    )
    active_after = client.get("/assurance/candidates?active_only=true")

    assert created.status_code == 200
    assert active_before.json() == []
    assert reviewed.json()["status"] == "active"
    assert [case["case_id"] for case in active_after.json()] == [created.json()["case_id"]]


def test_assurance_report_and_verify_are_report_only_and_tamper_evident(tmp_path: Path) -> None:
    client = TestClient(create_app(EventLog(tmp_path / "events.sqlite")))
    report = client.post(
        "/assurance/report",
        json={
            "baseline": _manifest("baseline", ["inspect"]),
            "candidate": _manifest("candidate", ["inspect"]),
            "replays": [
                {
                    "case_id": 1,
                    "passed": True,
                    "allowed_safe": 1,
                    "blocked_safe": 0,
                    "stopped_unsafe": 1,
                    "missed_unsafe": 0,
                    "step_decisions": ["allow", "halt"],
                }
            ],
        },
    )

    verified = client.post("/assurance/verify", json=report.json())
    tampered = {**report.json(), "verdict": "fail"}
    rejected = client.post("/assurance/verify", json=tampered)

    assert report.status_code == 200
    assert report.json()["verdict"] == "pass"
    assert verified.json() == {"valid": True}
    assert rejected.json() == {"valid": False}
