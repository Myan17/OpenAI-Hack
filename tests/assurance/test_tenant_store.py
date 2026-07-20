"""Additive tenant-scoped persistence must never enumerate another workspace."""

import sqlite3

from interlock.assurance.tenant_store import TenantCaseStore, TenantRegistry
from interlock.assurance.tenancy import TenantContext
import pytest


def test_tenant_case_store_scopes_writes_and_reads_by_workspace(tmp_path) -> None:
    store = TenantCaseStore(tmp_path / "tenant.sqlite")
    acme = TenantContext(tenant_id="acme", workspace_id="prod", subject_id="a", role="developer")
    bravo = TenantContext(tenant_id="bravo", workspace_id="prod", subject_id="b", role="developer")

    created = store.create(acme, title="Acme incident", summary="Scoped evidence.")

    assert [case.title for case in store.list(acme)] == ["Acme incident"]
    assert store.list(bravo) == []
    assert created.tenant_id == "acme"
    assert store.get(acme, created.case_id).title == "Acme incident"
    assert store.get(bravo, created.case_id) is None


def test_viewer_cannot_create_tenant_case(tmp_path) -> None:
    store = TenantCaseStore(tmp_path / "tenant.sqlite")
    viewer = TenantContext(tenant_id="acme", workspace_id="prod", subject_id="viewer", role="viewer")

    with pytest.raises(PermissionError):
        store.create(viewer, title="Denied", summary="View-only account.")


def test_registry_binds_workspace_membership_to_one_tenant(tmp_path) -> None:
    registry = TenantRegistry(tmp_path / "tenant.sqlite")
    registry.create_tenant("acme")
    registry.create_workspace("acme", "prod")
    registry.add_membership("acme", "prod", "subject-1", "developer")

    context = registry.context_for("subject-1", "acme", "prod")

    assert context is not None and context.role == "developer"
    assert registry.context_for("subject-1", "other", "prod") is None


def test_registry_rejects_orphaned_workspaces_and_memberships(tmp_path) -> None:
    registry = TenantRegistry(tmp_path / "tenant.sqlite")

    with pytest.raises(sqlite3.IntegrityError):
        registry.create_workspace("unknown", "prod")

    registry.create_tenant("acme")
    with pytest.raises(sqlite3.IntegrityError):
        registry.add_membership("acme", "unknown", "subject-1", "developer")
