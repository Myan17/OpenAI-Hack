"""Default-deny fixture authorization against durable tenant memberships."""

from collections.abc import Mapping

from interlock.assurance.tenancy import FixtureIdentityAdapter, TenantContext
from interlock.assurance.tenant_store import TenantRegistry


class TenantRequestAuthorizer:
    """Resolve fixture claims only when their exact durable membership agrees."""

    def __init__(self, registry: TenantRegistry) -> None:
        self._registry = registry
        self._identity = FixtureIdentityAdapter()

    def authorize(self, claims: Mapping[str, object]) -> TenantContext:
        claimed = self._identity.context_from_claims(dict(claims))
        membership = self._registry.context_for(
            claimed.subject_id, claimed.tenant_id, claimed.workspace_id
        )
        if membership is None:
            raise PermissionError("fixture identity has no membership in this tenant workspace")
        if membership.role != claimed.role:
            raise PermissionError("fixture identity role does not match durable membership")
        return membership
