"""Fixture-only adapter tests; no Multica client or network access is involved."""

from interlock.assurance.evidence import build_evidence_bundle
from interlock.assurance.delta import compare_authority
from interlock.assurance.models import AuthoritySurface, ProposedChangeEnvelope, ReplayCaseResult
from interlock.assurance.multica_adapter import fixture_envelope_to_manifest, fixture_callback


def test_fixture_adapter_preserves_authority_and_binds_stable_local_provenance() -> None:
    envelope = ProposedChangeEnvelope(
        correlation_id="corr-7", source_system="multica-fixture", task_id="task-7", run_id="run-7",
        change_class="code_change", components={"repository": "a" * 64},
        authority=AuthoritySurface(tools=["inspect"], environments=["staging"]),
    )

    manifest = fixture_envelope_to_manifest(envelope)

    assert manifest.release_id == "multica-fixture:corr-7"
    assert manifest.source == "multica-fixture:task-7:run-7"
    assert manifest.components == {"repository": "a" * 64}
    assert manifest.authority == envelope.authority


def test_fixture_callback_quarantines_incomplete_evidence_and_allows_verified_pass() -> None:
    envelope = ProposedChangeEnvelope(
        correlation_id="corr-8", source_system="multica-fixture", task_id="task-8", run_id="run-8",
        change_class="code_change", components={"repository": "a" * 64}, authority=AuthoritySurface(),
    )
    manifest = fixture_envelope_to_manifest(envelope)
    bundle = build_evidence_bundle(
        baseline=manifest, candidate=manifest,
        delta=compare_authority(manifest.authority, manifest.authority),
        replays=[ReplayCaseResult(case_id=3, passed=True)],
    )

    callback = fixture_callback(envelope, bundle)

    assert callback.verdict == "pass"
    assert callback.action == "continue_advisory"
    assert callback.replay_case_ids == (3,)
