"""Additive tenant-scoped persistence must never enumerate another workspace."""

from interlock.assurance.tenant_store import TenantCaseStore
from interlock.assurance.tenancy import TenantContext


def test_tenant_case_store_scopes_writes_and_reads_by_workspace(tmp_path) -> None:
    store = TenantCaseStore(tmp_path / "tenant.sqlite")
    acme = TenantContext(tenant_id="acme", workspace_id="prod", subject_id="a", role="developer")
    bravo = TenantContext(tenant_id="bravo", workspace_id="prod", subject_id="b", role="developer")

    created = store.create(acme, title="Acme incident", summary="Scoped evidence.")

    assert [case.title for case in store.list(acme)] == ["Acme incident"]
    assert store.list(bravo) == []
    assert created.tenant_id == "acme"
