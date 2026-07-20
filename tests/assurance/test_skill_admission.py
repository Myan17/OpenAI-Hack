"""Skill admission must remain reviewer-governed and evidence-backed."""

from interlock.assurance.models import AssuranceCase, AuthoritySurface, ProposedChangeEnvelope, ReplayCaseResult
from interlock.assurance.multica_adapter import fixture_envelope_to_manifest
from interlock.assurance.skill_admission import evaluate_skill_admission


def test_only_active_reviewer_approved_case_can_admit_a_verified_skill() -> None:
    envelope = ProposedChangeEnvelope(
        correlation_id="skill-1", source_system="multica-fixture", task_id="task-1", run_id="run-1",
        change_class="skill_admission", components={"skill": "a" * 64}, authority=AuthoritySurface(),
    )
    case = AssuranceCase(case_id=7, title="Skill safety", summary="Reviewed fixture.", source="fixture", owner="qa", status="active", reviewer="reviewer")

    decision = evaluate_skill_admission(envelope, fixture_envelope_to_manifest(envelope), case, [ReplayCaseResult(case_id=7, passed=True)])

    assert decision.admissible is True
    assert decision.callback.action == "continue_advisory"


def test_unreviewed_skill_case_is_quarantined() -> None:
    envelope = ProposedChangeEnvelope(
        correlation_id="skill-2", source_system="multica-fixture", task_id="task-2", run_id="run-2",
        change_class="skill_admission", components={"skill": "b" * 64}, authority=AuthoritySurface(),
    )
    case = AssuranceCase(case_id=8, title="Unreviewed", summary="Not active.", source="fixture", owner="qa", status="pending_review")

    decision = evaluate_skill_admission(envelope, fixture_envelope_to_manifest(envelope), case, [])

    assert decision.admissible is False
    assert decision.callback.action == "quarantine"
