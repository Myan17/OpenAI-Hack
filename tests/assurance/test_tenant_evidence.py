"""Tenant-bound evidence must be tamper-evident and non-replayable across scopes."""

from interlock.assurance.delta import compare_authority
from interlock.assurance.evidence import build_evidence_bundle
from interlock.assurance.models import AuthoritySurface, ChangeManifest, ReplayCaseResult
from interlock.assurance.tenant_evidence import bind_tenant_evidence, verify_tenant_evidence
from interlock.assurance.tenancy import TenantContext


def _evidence_fixture():
    manifest = ChangeManifest(
        release_id="release-1",
        source="fixture",
        components={"policy": "a" * 64},
        authority=AuthoritySurface(tools=["inspect"]),
    )
    return build_evidence_bundle(
        baseline=manifest,
        candidate=manifest,
        delta=compare_authority(manifest.authority, manifest.authority),
        replays=[ReplayCaseResult(case_id=1, passed=True)],
    )


def test_tenant_evidence_verifies_only_in_the_bound_workspace() -> None:
    acme = TenantContext(tenant_id="acme", workspace_id="prod", subject_id="reviewer", role="assurance_reviewer")
    other_workspace = acme.model_copy(update={"workspace_id": "dev"})
    evidence = bind_tenant_evidence(acme, _evidence_fixture())

    assert verify_tenant_evidence(acme, evidence) is True
    assert verify_tenant_evidence(other_workspace, evidence) is False


def test_tenant_evidence_rejects_scope_and_evidence_digest_tampering() -> None:
    context = TenantContext(tenant_id="acme", workspace_id="prod", subject_id="reviewer", role="assurance_reviewer")
    evidence = bind_tenant_evidence(context, _evidence_fixture())

    assert verify_tenant_evidence(context, evidence.model_copy(update={"workspace_id": "other"})) is False
    assert verify_tenant_evidence(context, evidence.model_copy(update={"scope_digest": "0" * 64})) is False
