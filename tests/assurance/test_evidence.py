"""Tests for tamper-evident, report-only release evidence bundles."""

from interlock.assurance.delta import compare_authority
from interlock.assurance.evidence import build_evidence_bundle, verify_evidence_bundle
from interlock.assurance.models import AuthoritySurface, ChangeManifest, ReplayCaseResult


def test_evidence_bundle_verifies_and_detects_tampering() -> None:
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
        authority=AuthoritySurface(tools=["inspect", "db"]),
    )
    bundle = build_evidence_bundle(
        baseline=baseline,
        candidate=candidate,
        delta=compare_authority(baseline.authority, candidate.authority),
        replays=[ReplayCaseResult(case_id=1, passed=True)],
    )

    assert verify_evidence_bundle(bundle) is True

    tampered = bundle.model_copy(update={"verdict": "pass"})

    assert verify_evidence_bundle(tampered) is False
