"""Foundational multi-tenant contracts are strict and default-deny."""

import pytest
from pydantic import ValidationError

from interlock.assurance.tenancy import FixtureIdentityAdapter, TenantContext, require_role


def test_tenant_context_is_immutable_and_requires_scope_and_subject() -> None:
    context = TenantContext(tenant_id="tenant-acme", workspace_id="workspace-prod", subject_id="subject-1", role="assurance_reviewer")

    assert context.tenant_id == "tenant-acme"
    with pytest.raises(ValidationError):
        TenantContext(tenant_id="", workspace_id="workspace-prod", subject_id="subject-1", role="viewer")
    with pytest.raises(ValidationError):
        TenantContext(tenant_id="tenant-acme", workspace_id="workspace-prod", subject_id="subject-1", role="owner")


def test_role_check_default_denies_unlisted_roles() -> None:
    reviewer = TenantContext(tenant_id="tenant-acme", workspace_id="workspace-prod", subject_id="subject-1", role="assurance_reviewer")
    viewer = TenantContext(tenant_id="tenant-acme", workspace_id="workspace-prod", subject_id="subject-2", role="viewer")

    require_role(reviewer, "assurance_reviewer", "tenant_admin")
    with pytest.raises(PermissionError, match="role"):
        require_role(viewer, "assurance_reviewer")


def test_fixture_identity_adapter_requires_complete_scope_claims() -> None:
    adapter = FixtureIdentityAdapter()

    context = adapter.context_from_claims({"tenant_id": "tenant-acme", "workspace_id": "workspace-prod", "subject_id": "subject-1", "role": "developer"})

    assert context.role == "developer"
    with pytest.raises(ValueError, match="missing"):
        adapter.context_from_claims({"tenant_id": "tenant-acme"})
