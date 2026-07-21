"""Fixture identities must resolve to a durable, exact tenant membership."""

import pytest

from interlock.assurance.tenant_authorization import TenantRequestAuthorizer
from interlock.assurance.tenant_store import TenantRegistry


def _claims(**changes: str) -> dict[str, str]:
    claims = {
        "tenant_id": "acme",
        "workspace_id": "staging",
        "subject_id": "subject-1",
        "role": "developer",
    }
    claims.update(changes)
    return claims


def test_fixture_identity_is_authorized_only_when_exact_membership_exists(tmp_path) -> None:
    registry = TenantRegistry(tmp_path / "tenant.sqlite")
    registry.create_tenant("acme")
    registry.create_workspace("acme", "staging")
    registry.add_membership("acme", "staging", "subject-1", "developer")

    context = TenantRequestAuthorizer(registry).authorize(_claims())

    assert (context.tenant_id, context.workspace_id, context.subject_id, context.role) == (
        "acme", "staging", "subject-1", "developer"
    )


def test_fixture_identity_fails_closed_for_unknown_or_role_mismatched_membership(tmp_path) -> None:
    registry = TenantRegistry(tmp_path / "tenant.sqlite")
    registry.create_tenant("acme")
    registry.create_workspace("acme", "staging")
    registry.add_membership("acme", "staging", "subject-1", "developer")
    authorizer = TenantRequestAuthorizer(registry)

    with pytest.raises(PermissionError):
        authorizer.authorize(_claims(role="tenant_admin"))
    with pytest.raises(PermissionError):
        authorizer.authorize(_claims(subject_id="unknown"))


def test_fixture_identity_fails_closed_when_its_tenant_is_suspended(tmp_path) -> None:
    registry = TenantRegistry(tmp_path / "tenant.sqlite")
    registry.create_tenant("acme")
    registry.create_workspace("acme", "staging")
    registry.add_membership("acme", "staging", "subject-1", "developer")
    registry.set_tenant_status("acme", "suspended")

    with pytest.raises(PermissionError):
        TenantRequestAuthorizer(registry).authorize(_claims())
