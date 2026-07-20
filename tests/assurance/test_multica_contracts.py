"""Strict local contracts for a future Multica-shaped orchestration adapter."""

import pytest
from pydantic import ValidationError

from interlock.assurance.models import AdvisoryCallback, AuthoritySurface, ProposedChangeEnvelope


def test_fixture_envelope_is_canonical_and_rejects_prompt_like_extra_fields() -> None:
    envelope = ProposedChangeEnvelope(
        correlation_id="corr-001",
        source_system="multica-fixture",
        task_id="task-1",
        run_id="run-1",
        change_class="skill_admission",
        components={"skill": "a" * 64},
        authority=AuthoritySurface(tools=["inspect"]),
    )

    assert envelope.provenance == "fixture"
    assert len(envelope.digest) == 64
    with pytest.raises(ValidationError):
        ProposedChangeEnvelope.model_validate({**envelope.model_dump(), "raw_prompt": "ignore policy"})


def test_advisory_callback_requires_evidence_and_uses_fixed_actions() -> None:
    callback = AdvisoryCallback(
        correlation_id="corr-001",
        verdict="inconclusive",
        action="quarantine",
        reason_codes=["missing_provenance"],
        evidence_digest="b" * 64,
    )

    assert callback.reason_codes == ("missing_provenance",)
    with pytest.raises(ValidationError):
        AdvisoryCallback(
            correlation_id="corr-001", verdict="pass", action="continue_advisory",
            reason_codes=[], evidence_digest="not-a-digest",
        )
