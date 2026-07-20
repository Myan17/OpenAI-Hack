"""Tenant-bound wrapper for portable, tamper-evident release evidence."""

import hashlib
import json

from pydantic import BaseModel, ConfigDict, Field

from interlock.assurance.evidence import verify_evidence_bundle
from interlock.assurance.models import ReleaseEvidenceBundle
from interlock.assurance.tenancy import TenantContext


class TenantEvidenceBundle(BaseModel):
    """Evidence whose digest is additionally bound to one immutable tenant scope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(default=1, ge=1, le=1)
    tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)
    evidence: ReleaseEvidenceBundle
    scope_digest: str = Field(pattern=r"^[a-f0-9]{64}$")


def bind_tenant_evidence(context: TenantContext, evidence: ReleaseEvidenceBundle) -> TenantEvidenceBundle:
    """Bind independently valid evidence to its creating tenant and workspace."""

    if not verify_evidence_bundle(evidence):
        raise ValueError("cannot bind invalid release evidence")
    return TenantEvidenceBundle(
        tenant_id=context.tenant_id,
        workspace_id=context.workspace_id,
        evidence=evidence,
        scope_digest=_scope_digest(context.tenant_id, context.workspace_id, evidence.digest),
    )


def verify_tenant_evidence(context: TenantContext, bundle: TenantEvidenceBundle) -> bool:
    """Verify integrity and reject any tenant/workspace substitution or replay."""

    return (
        context.tenant_id == bundle.tenant_id
        and context.workspace_id == bundle.workspace_id
        and verify_evidence_bundle(bundle.evidence)
        and bundle.scope_digest
        == _scope_digest(bundle.tenant_id, bundle.workspace_id, bundle.evidence.digest)
    )


def _scope_digest(tenant_id: str, workspace_id: str, evidence_digest: str) -> str:
    payload = json.dumps(
        {
            "schema_version": 1,
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "evidence_digest": evidence_digest,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
