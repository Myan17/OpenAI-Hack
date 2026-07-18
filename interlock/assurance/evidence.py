"""Tamper-evident, local release evidence bundle construction and verification."""

import hashlib
import json

from interlock.assurance.models import (
    AuthorityDelta,
    ChangeManifest,
    ReleaseEvidenceBundle,
    ReplayCaseResult,
)


def build_evidence_bundle(
    *,
    baseline: ChangeManifest,
    candidate: ChangeManifest,
    delta: AuthorityDelta,
    replays: list[ReplayCaseResult],
) -> ReleaseEvidenceBundle:
    """Build an explainable advisory verdict and bind it to canonical evidence."""

    verdict = _verdict_for(delta, replays)
    payload = {
        "schema_version": 1,
        "baseline": baseline.model_dump(mode="json"),
        "candidate": candidate.model_dump(mode="json"),
        "delta": delta.model_dump(mode="json"),
        "replays": [replay.model_dump(mode="json") for replay in replays],
        "verdict": verdict,
    }
    digest = _digest_payload(payload)
    return ReleaseEvidenceBundle(
        baseline=baseline,
        candidate=candidate,
        delta=delta,
        replays=tuple(replays),
        verdict=verdict,
        digest=digest,
    )


def verify_evidence_bundle(bundle: ReleaseEvidenceBundle) -> bool:
    """Verify integrity and recompute the deterministic release verdict locally."""

    expected_verdict = _verdict_for(bundle.delta, list(bundle.replays))
    expected_digest = _digest_payload(
        json.loads(bundle.canonical_json_without_digest())
    )
    return bundle.verdict == expected_verdict and bundle.digest == expected_digest


def _verdict_for(delta: AuthorityDelta, replays: list[ReplayCaseResult]) -> str:
    """Return an advisory verdict; any expansion or failed required replay fails safely."""

    if delta.has_expansion or any(not replay.passed for replay in replays):
        return "fail"
    return "pass" if replays else "inconclusive"


def _digest_payload(payload: dict[str, object]) -> str:
    """Hash a canonical JSON payload without relying on server-side state."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
