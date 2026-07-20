"""Pure local skill-admission decision; no orchestration or runtime side effects."""

from dataclasses import dataclass

from interlock.assurance.models import AdvisoryCallback, AssuranceCase, ChangeManifest, ProposedChangeEnvelope, ReplayCaseResult, ReleaseEvidenceBundle
from interlock.assurance.multica_adapter import evaluate_fixture_change


@dataclass(frozen=True)
class SkillAdmissionDecision:
    """Evidence-backed admission result for a reusable skill candidate."""

    admissible: bool
    callback: AdvisoryCallback
    evidence: ReleaseEvidenceBundle | None


def evaluate_skill_admission(
    envelope: ProposedChangeEnvelope,
    baseline: ChangeManifest,
    case: AssuranceCase,
    replays: list[ReplayCaseResult],
) -> SkillAdmissionDecision:
    """Admit only active reviewer-approved skill evidence; otherwise quarantine safely."""

    if envelope.change_class != "skill_admission":
        raise ValueError("skill admission requires a skill_admission envelope")
    if case.status != "active" or case.reviewer is None:
        return SkillAdmissionDecision(
            admissible=False,
            callback=AdvisoryCallback(
                correlation_id=envelope.correlation_id, verdict="inconclusive", action="quarantine",
                reason_codes=("skill_case_not_active",), evidence_digest="0" * 64,
            ),
            evidence=None,
        )
    evidence, callback = evaluate_fixture_change(envelope, baseline, replays)
    return SkillAdmissionDecision(
        admissible=callback.verdict == "pass" and callback.action == "continue_advisory",
        callback=callback,
        evidence=evidence,
    )
