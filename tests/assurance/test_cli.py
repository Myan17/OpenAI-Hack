"""Tests for the local-only assurance CLI used by a CI job."""

import json
from pathlib import Path

from interlock.assurance.cli import main
from interlock.assurance.delta import compare_authority
from interlock.assurance.evidence import build_evidence_bundle
from interlock.assurance.models import AuthoritySurface, ChangeManifest, ReplayCaseResult


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
