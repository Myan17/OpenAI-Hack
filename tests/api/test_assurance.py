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


def test_assurance_replay_uses_the_existing_effect_free_simulator(tmp_path: Path) -> None:
    client = TestClient(create_app(EventLog(tmp_path / "events.sqlite")))

    response = client.post(
        "/assurance/replay",
        json={
            "case_id": 9,
            "policy": {"task": "inspect", "allowed_tools": ["inspect"]},
            "steps": [
                {
                    "id": "read",
                    "description": "Read the ledger.",
                    "expected_safe": True,
                    "action": {"tool": "inspect", "args": {"resource": "ledger"}},
                    "context": {},
                },
                {
                    "id": "drop",
                    "description": "Drop a table.",
                    "expected_safe": False,
                    "action": {"tool": "db", "args": {"sql": "DROP TABLE users"}},
                    "context": {},
                },
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["passed"] is True
    assert response.json()["step_decisions"] == ["allow", "halt"]
    assert client.get("/events").json() == []


def test_approved_candidate_can_receive_and_run_a_replay_fixture(tmp_path: Path) -> None:
    client = TestClient(create_app(EventLog(tmp_path / "events.sqlite")))
    created = client.post(
        "/assurance/candidates",
        json={"title": "Preserve ledger read", "summary": "Ledger read stays allowed.", "source": "event:17", "owner": "qa@example.test"},
    )
    case_id = created.json()["case_id"]
    client.post(f"/assurance/candidates/{case_id}/approved", json={"reviewer": "reviewer@example.test"})

    attached = client.post(
        f"/assurance/candidates/{case_id}/fixtures/attach",
        json={
            "policy": {"task": "inspect", "allowed_tools": ["inspect"]},
            "steps": [{
                "id": "read", "description": "Read ledger.", "expected_safe": True,
                "action": {"tool": "inspect", "args": {"resource": "ledger"}}, "context": {},
            }],
        },
    )
    replayed = client.post(f"/assurance/candidates/{case_id}/fixtures/replay")

    assert attached.status_code == 200
    assert replayed.json()["passed"] is True


def test_assurance_lifecycle_api_expires_retires_and_aggregates_trials(tmp_path: Path) -> None:
    client = TestClient(create_app(EventLog(tmp_path / "events.sqlite")))
    created = client.post(
        "/assurance/candidates",
        json={
            "title": "Lifecycle case", "summary": "A safe fixture has bounded lifetime.",
            "source": "event:21", "owner": "qa@example.test", "expires_at_epoch": 10,
        },
    )
    case_id = created.json()["case_id"]
    client.post(f"/assurance/candidates/{case_id}/approved", json={"reviewer": "reviewer@example.test"})

    expired = client.post("/assurance/candidates/expire", json={"now_epoch": 11})
    audit = client.get(f"/assurance/candidates/{case_id}/history/audit")

    assert expired.json() == {"expired_count": 1}
    assert audit.json()[-1]["action"] == "expired"


def test_assurance_lifecycle_api_retires_only_active_cases_with_an_audit_record(tmp_path: Path) -> None:
    client = TestClient(create_app(EventLog(tmp_path / "events.sqlite")))
    created = client.post(
        "/assurance/candidates",
        json={"title": "Retirable case", "summary": "Retirement remains audited.", "source": "event:22", "owner": "qa"},
    )
    case_id = created.json()["case_id"]
    client.post(f"/assurance/candidates/{case_id}/approved", json={"reviewer": "reviewer"})

    retired = client.post(f"/assurance/candidates/{case_id}/retire", json={"actor": "qa"})
    active = client.get("/assurance/candidates?active_only=true")
    audit = client.get(f"/assurance/candidates/{case_id}/history/audit")
    repeat = client.post(f"/assurance/candidates/{case_id}/retire", json={"actor": "qa"})

    assert retired.status_code == 200
    assert retired.json()["status"] == "retired"
    assert active.json() == []
    assert audit.json()[-1]["action"] == "retired"
    assert repeat.status_code == 409


def test_assurance_check_returns_local_advisory_payload(tmp_path: Path) -> None:
    client = TestClient(create_app(EventLog(tmp_path / "events.sqlite")))
    report = client.post(
        "/assurance/report",
        json={
            "baseline": _manifest("baseline", ["inspect"]),
            "candidate": _manifest("candidate", ["inspect"]),
            "replays": [{"case_id": 1, "passed": True}],
        },
    )

    response = client.post("/assurance/check", json=report.json())

    assert response.status_code == 200
    assert response.json()["conclusion"] == "success"
    assert response.json()["advisory"] is True
