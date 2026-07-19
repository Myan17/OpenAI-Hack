"""Tests for the local-only assurance CLI used by a CI job."""

import json
from pathlib import Path

from interlock.assurance.cli import main
from interlock.assurance.delta import compare_authority
from interlock.assurance.evidence import build_evidence_bundle
from interlock.assurance.models import AuthoritySurface, ChangeManifest, ReplayCaseResult
from interlock.engine.models import Policy
from interlock.engine.simulator import developer_agent_trace


def test_cli_verifies_a_bundle_and_rejects_tampered_evidence(tmp_path: Path, capsys) -> None:
    baseline = ChangeManifest(
        release_id="baseline",
        source="fixture",
        components={"policy": "a" * 64},
        authority=AuthoritySurface(tools=["inspect"]),
    )
    candidate = ChangeManifest(
        release_id="candidate",
        source="fixture",
        components={"policy": "b" * 64},
        authority=AuthoritySurface(tools=["inspect"]),
    )
    bundle = build_evidence_bundle(
        baseline=baseline,
        candidate=candidate,
        delta=compare_authority(baseline.authority, candidate.authority),
        replays=[ReplayCaseResult(case_id=1, passed=True)],
    )
    path = tmp_path / "bundle.json"
    path.write_text(bundle.model_dump_json(), encoding="utf-8")

    assert main(["verify", str(path)]) == 0
    assert json.loads(capsys.readouterr().out) == {"valid": True}

    tampered = bundle.model_dump(mode="json")
    tampered["verdict"] = "fail"
    path.write_text(json.dumps(tampered), encoding="utf-8")

    assert main(["verify", str(path)]) == 1
    assert json.loads(capsys.readouterr().out) == {"valid": False}


def test_cli_captures_and_reviews_a_candidate_without_runtime_authority(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "assurance.sqlite"

    assert main([
        "case-create", "--db", str(db_path), "--title", "Preserve safe read",
        "--summary", "The ledger read remains permitted.", "--source", "cli:test", "--owner", "qa@example.test",
    ]) == 0
    created = json.loads(capsys.readouterr().out)

    assert created["status"] == "pending_review"
    assert main([
        "case-review", "--db", str(db_path), "--case-id", str(created["case_id"]),
        "--resolution", "approved", "--reviewer", "reviewer@example.test",
    ]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "active"


def test_cli_completes_the_local_candidate_fixture_replay_and_retirement_flow(
    tmp_path: Path, capsys
) -> None:
    db_path = tmp_path / "assurance.sqlite"
    policy_path = tmp_path / "policy.json"
    steps_path = tmp_path / "steps.json"
    policy_path.write_text(
        Policy(
            task="fixture replay",
            allowed_tools={"inspect"},
            allowed_environments={"staging"},
        ).model_dump_json(),
        encoding="utf-8",
    )
    steps_path.write_text(
        json.dumps([step.model_dump(mode="json") for step in developer_agent_trace()]),
        encoding="utf-8",
    )

    assert main([
        "case-create", "--db", str(db_path), "--title", "Known safe path",
        "--summary", "A reviewed local fixture.", "--source", "cli:test", "--owner", "qa",
    ]) == 0
    case_id = json.loads(capsys.readouterr().out)["case_id"]
    assert main([
        "case-review", "--db", str(db_path), "--case-id", str(case_id),
        "--resolution", "approved", "--reviewer", "reviewer",
    ]) == 0
    capsys.readouterr()

    assert main([
        "fixture-attach", "--db", str(db_path), "--case-id", str(case_id),
        "--policy", str(policy_path), "--steps", str(steps_path),
    ]) == 0
    assert json.loads(capsys.readouterr().out) == {"attached": True, "case_id": case_id}

    assert main(["case-replay", "--db", str(db_path), "--case-id", str(case_id)]) == 0
    assert json.loads(capsys.readouterr().out)["passed"] is True

    assert main(["case-retire", "--db", str(db_path), "--case-id", str(case_id), "--actor", "qa"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "retired"

    assert main(["case-audit", "--db", str(db_path), "--case-id", str(case_id)]) == 0
    assert [event["action"] for event in json.loads(capsys.readouterr().out)] == [
        "created", "approved", "retired"
    ]


def test_cli_exports_an_empty_snapshot_and_imports_it_into_an_empty_store(tmp_path: Path, capsys) -> None:
    source = tmp_path / "source.sqlite"
    snapshot = tmp_path / "snapshot.json"
    restored = tmp_path / "restored.sqlite"

    assert main(["snapshot-export", "--db", str(source), "--output", str(snapshot)]) == 0
    assert json.loads(capsys.readouterr().out)["exported"] is True
    assert main(["snapshot-import", "--db", str(restored), "--input", str(snapshot)]) == 0
    assert json.loads(capsys.readouterr().out) == {"imported_cases": 0}
