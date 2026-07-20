"""Fixture-only adapter tests; no Multica client or network access is involved."""

from interlock.assurance.models import AuthoritySurface, ProposedChangeEnvelope
from interlock.assurance.multica_adapter import fixture_envelope_to_manifest


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
