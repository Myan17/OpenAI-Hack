"""Pure fixture adapter boundary for a future Multica integration."""

from interlock.assurance.evidence import verify_evidence_bundle
from interlock.assurance.delta import compare_authority
from interlock.assurance.evidence import build_evidence_bundle
from interlock.assurance.models import AdvisoryCallback, ChangeManifest, ProposedChangeEnvelope, ReleaseEvidenceBundle, ReplayCaseResult


def fixture_envelope_to_manifest(envelope: ProposedChangeEnvelope) -> ChangeManifest:
    """Convert trusted local fixture data without reading a daemon, API, or clock."""

    return ChangeManifest(
        release_id=f"multica-fixture:{envelope.correlation_id}",
        source=f"multica-fixture:{envelope.task_id}:{envelope.run_id}",
        components=envelope.components,
        authority=envelope.authority,
    )


def fixture_callback(envelope: ProposedChangeEnvelope, bundle: ReleaseEvidenceBundle) -> AdvisoryCallback:
    """Create a fail-safe local advisory result from independently verifiable evidence."""

    if not verify_evidence_bundle(bundle):
        return AdvisoryCallback(
            correlation_id=envelope.correlation_id,
            verdict="inconclusive",
            action="quarantine",
            reason_codes=("invalid_evidence",),
            evidence_digest=bundle.digest,
        )
    if bundle.verdict == "pass":
        action = "continue_advisory"
        reasons = ("evidence_verified",)
    elif bundle.verdict == "fail":
        action = "reviewer_required"
        reasons = ("release_check_failed",)
    else:
        action = "quarantine"
        reasons = ("incomplete_evidence",)
    return AdvisoryCallback(
        correlation_id=envelope.correlation_id,
        verdict=bundle.verdict,
        action=action,
        reason_codes=reasons,
        evidence_digest=bundle.digest,
        replay_case_ids=tuple(replay.case_id for replay in bundle.replays),
    )


def evaluate_fixture_change(
    envelope: ProposedChangeEnvelope,
    baseline: ChangeManifest,
    replays: list[ReplayCaseResult],
) -> tuple[ReleaseEvidenceBundle, AdvisoryCallback]:
    """Compose local-only delta, replay evidence, and an advisory action without dispatching work."""

    candidate = fixture_envelope_to_manifest(envelope)
    bundle = build_evidence_bundle(
        baseline=baseline,
        candidate=candidate,
        delta=compare_authority(baseline.authority, candidate.authority),
        replays=replays,
    )
    return bundle, fixture_callback(envelope, bundle)
