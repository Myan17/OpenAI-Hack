"""Strict tenant/workspace authorization contracts, independent of transport identity."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TenantRole = Literal["tenant_admin", "assurance_reviewer", "developer", "viewer", "service"]


class TenantContext(BaseModel):
    """Verified scope required by future protected persistence and API operations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)
    subject_id: str = Field(min_length=1, max_length=256)
    role: TenantRole


def require_role(context: TenantContext, *allowed_roles: TenantRole) -> None:
    """Default-deny authorization guard for future tenant-scoped operations."""

    if context.role not in allowed_roles:
        raise PermissionError("tenant context role is not authorized for this operation")


class FixtureIdentityAdapter:
    """Local test-double for a future Entra-backed identity adapter."""

    _REQUIRED_CLAIMS = ("tenant_id", "workspace_id", "subject_id", "role")

    def context_from_claims(self, claims: dict[str, object]) -> TenantContext:
        """Construct scope only when every required claim is present and typed as a string."""

        missing = [claim for claim in self._REQUIRED_CLAIMS if not isinstance(claims.get(claim), str)]
        if missing:
            raise ValueError("missing or invalid fixture identity claims")
        return TenantContext(
            tenant_id=str(claims["tenant_id"]),
            workspace_id=str(claims["workspace_id"]),
            subject_id=str(claims["subject_id"]),
            role=str(claims["role"]),
        )
