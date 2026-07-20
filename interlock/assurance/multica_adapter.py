"""Pure fixture adapter boundary for a future Multica integration."""

from interlock.assurance.models import ChangeManifest, ProposedChangeEnvelope


def fixture_envelope_to_manifest(envelope: ProposedChangeEnvelope) -> ChangeManifest:
    """Convert trusted local fixture data without reading a daemon, API, or clock."""

    return ChangeManifest(
        release_id=f"multica-fixture:{envelope.correlation_id}",
        source=f"multica-fixture:{envelope.task_id}:{envelope.run_id}",
        components=envelope.components,
        authority=envelope.authority,
    )
