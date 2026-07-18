"""Tests for the local GitHub-Check-compatible advisory adapter."""

from interlock.assurance.check import build_advisory_check
from interlock.assurance.delta import compare_authority
from interlock.assurance.evidence import build_evidence_bundle
from interlock.assurance.models import AuthoritySurface, ChangeManifest, ReplayCaseResult


def _manifest(release_id: str, tools: list[str]) -> ChangeManifest:
    return ChangeManifest(
        release_id=release_id,
        source="fixture",
        components={"policy": ("a" if release_id == "base" else "b") * 64},
        authority=AuthoritySurface(tools=tools),
    )


def test_advisory_check_maps_passing_evidence_to_success() -> None:
    baseline = _manifest("base", ["inspect"])
    candidate = _manifest("candidate", ["inspect"])
    bundle = build_evidence_bundle(
        baseline=baseline,
        candidate=candidate,
        delta=compare_authority(baseline.authority, candidate.authority),
        replays=[ReplayCaseResult(case_id=1, passed=True)],
    )

    check = build_advisory_check(bundle)

    assert check.conclusion == "success"
    assert check.advisory is True
    assert bundle.digest in check.summary


def test_advisory_check_maps_safety_regression_to_action_required() -> None:
    baseline = _manifest("base", ["inspect"])
    candidate = _manifest("candidate", ["inspect", "db"])
    bundle = build_evidence_bundle(
        baseline=baseline,
        candidate=candidate,
        delta=compare_authority(baseline.authority, candidate.authority),
        replays=[ReplayCaseResult(case_id=1, passed=True)],
    )

    check = build_advisory_check(bundle)

    assert check.conclusion == "action_required"
