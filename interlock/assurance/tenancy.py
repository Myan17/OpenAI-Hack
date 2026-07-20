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
