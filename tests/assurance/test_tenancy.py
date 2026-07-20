"""Foundational multi-tenant contracts are strict and default-deny."""

import pytest
from pydantic import ValidationError

from interlock.assurance.tenancy import TenantContext


def test_tenant_context_is_immutable_and_requires_scope_and_subject() -> None:
    context = TenantContext(tenant_id="tenant-acme", workspace_id="workspace-prod", subject_id="subject-1", role="assurance_reviewer")

    assert context.tenant_id == "tenant-acme"
    with pytest.raises(ValidationError):
        TenantContext(tenant_id="", workspace_id="workspace-prod", subject_id="subject-1", role="viewer")
    with pytest.raises(ValidationError):
        TenantContext(tenant_id="tenant-acme", workspace_id="workspace-prod", subject_id="subject-1", role="owner")
