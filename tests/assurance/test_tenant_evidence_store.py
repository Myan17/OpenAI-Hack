"""Tenant evidence persistence, export, and restore stay inside one workspace."""

import pytest

from interlock.assurance.delta import compare_authority
from interlock.assurance.evidence import build_evidence_bundle
from interlock.assurance.models import AuthoritySurface, ChangeManifest, ReplayCaseResult
from interlock.assurance.tenant_evidence import bind_tenant_evidence
from interlock.assurance.tenant_evidence_store import TenantEvidenceStore
from interlock.assurance.tenancy import TenantContext


def _context(tenant_id: str = "acme", workspace_id: str = "prod") -> TenantContext:
    return TenantContext(tenant_id=tenant_id, workspace_id=workspace_id, subject_id="reviewer", role="assurance_reviewer")


def _bundle(context: TenantContext):
    manifest = ChangeManifest(
        release_id="release-1", source="fixture", components={"policy": "a" * 64},
        authority=AuthoritySurface(tools=["inspect"]),
    )
    evidence = build_evidence_bundle(
        baseline=manifest, candidate=manifest,
        delta=compare_authority(manifest.authority, manifest.authority),
        replays=[ReplayCaseResult(case_id=1, passed=True)],
    )
    return bind_tenant_evidence(context, evidence)


def test_tenant_evidence_store_rejects_cross_scope_reads_and_replays(tmp_path) -> None:
    store = TenantEvidenceStore(tmp_path / "evidence.sqlite")
    acme = _context()
    bravo = _context("bravo")
    bundle = _bundle(acme)

    store.record(acme, bundle)

    assert store.get(acme, bundle.evidence.digest) == bundle
    assert store.get(bravo, bundle.evidence.digest) is None
    with pytest.raises(ValueError):
        store.record(bravo, bundle)


def test_tenant_evidence_snapshot_restores_only_into_its_empty_scope(tmp_path) -> None:
    acme = _context()
    source = TenantEvidenceStore(tmp_path / "source.sqlite")
    source.record(acme, _bundle(acme))
    snapshot = source.export_snapshot(acme)
    target = TenantEvidenceStore(tmp_path / "target.sqlite")

    assert target.import_snapshot(acme, snapshot) == 1
    assert target.export_snapshot(acme) == snapshot
    with pytest.raises(ValueError):
        target.import_snapshot(acme, snapshot)
    with pytest.raises(ValueError):
        TenantEvidenceStore(tmp_path / "other.sqlite").import_snapshot(_context("acme", "dev"), snapshot)
