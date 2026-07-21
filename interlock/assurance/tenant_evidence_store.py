"""Tenant-scoped persistence and recovery for tamper-evident release evidence."""

import json
import sqlite3
from pathlib import Path

from pydantic import TypeAdapter

from interlock.assurance.tenant_evidence import TenantEvidenceBundle, verify_tenant_evidence
from interlock.assurance.tenancy import TenantContext, require_role


_BUNDLES = TypeAdapter(list[TenantEvidenceBundle])
_WRITERS = ("tenant_admin", "assurance_reviewer", "developer", "service")


class TenantEvidenceStore:
    """Persist only independently valid evidence bound to the caller's workspace."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS tenant_release_evidence (
                tenant_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                evidence_digest TEXT NOT NULL,
                bundle_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, workspace_id, evidence_digest))"""
            )

    def record(self, context: TenantContext, bundle: TenantEvidenceBundle) -> None:
        """Store valid evidence without allowing a scope substitution."""

        require_role(context, *_WRITERS)
        if not verify_tenant_evidence(context, bundle):
            raise ValueError("tenant evidence is invalid or outside the current workspace")
        with sqlite3.connect(self._db_path) as connection:
            connection.execute(
                "INSERT OR IGNORE INTO tenant_release_evidence (tenant_id, workspace_id, evidence_digest, bundle_json) VALUES (?, ?, ?, ?)",
                (
                    context.tenant_id,
                    context.workspace_id,
                    bundle.evidence.digest,
                    bundle.model_dump_json(),
                ),
            )

    def get(self, context: TenantContext, evidence_digest: str) -> TenantEvidenceBundle | None:
        """Load one valid evidence bundle inside the caller's immutable scope."""

        with sqlite3.connect(self._db_path) as connection:
            row = connection.execute(
                "SELECT bundle_json FROM tenant_release_evidence WHERE tenant_id = ? AND workspace_id = ? AND evidence_digest = ?",
                (context.tenant_id, context.workspace_id, evidence_digest),
            ).fetchone()
        if row is None:
            return None
        try:
            bundle = TenantEvidenceBundle.model_validate_json(str(row[0]))
        except ValueError:
            return None
        return bundle if verify_tenant_evidence(context, bundle) else None

    def export_snapshot(self, context: TenantContext) -> dict[str, object]:
        """Export only one workspace's independently verifiable evidence."""

        require_role(context, *_WRITERS)
        with sqlite3.connect(self._db_path) as connection:
            rows = connection.execute(
                "SELECT bundle_json FROM tenant_release_evidence WHERE tenant_id = ? AND workspace_id = ? ORDER BY evidence_digest",
                (context.tenant_id, context.workspace_id),
            ).fetchall()
        bundles = [TenantEvidenceBundle.model_validate_json(str(row[0])) for row in rows]
        if any(not verify_tenant_evidence(context, bundle) for bundle in bundles):
            raise ValueError("stored tenant evidence failed verification")
        return {
            "schema_version": 1,
            "tenant_id": context.tenant_id,
            "workspace_id": context.workspace_id,
            "evidence": [bundle.model_dump(mode="json") for bundle in bundles],
        }

    def import_snapshot(self, context: TenantContext, snapshot: dict[str, object]) -> int:
        """Restore a verified workspace snapshot only into an empty target scope."""

        require_role(context, *_WRITERS)
        if (
            snapshot.get("schema_version") != 1
            or snapshot.get("tenant_id") != context.tenant_id
            or snapshot.get("workspace_id") != context.workspace_id
            or not isinstance(snapshot.get("evidence"), list)
        ):
            raise ValueError("tenant evidence snapshot scope or schema is invalid")
        try:
            bundles = _BUNDLES.validate_python(snapshot["evidence"])
        except ValueError as error:
            raise ValueError("tenant evidence snapshot is invalid") from error
        if any(not verify_tenant_evidence(context, bundle) for bundle in bundles):
            raise ValueError("tenant evidence snapshot failed verification")
        with sqlite3.connect(self._db_path) as connection:
            existing = connection.execute(
                "SELECT COUNT(*) FROM tenant_release_evidence WHERE tenant_id = ? AND workspace_id = ?",
                (context.tenant_id, context.workspace_id),
            ).fetchone()
            if existing is not None and int(existing[0]) != 0:
                raise ValueError("tenant evidence import requires an empty workspace target")
            for bundle in bundles:
                connection.execute(
                    "INSERT INTO tenant_release_evidence (tenant_id, workspace_id, evidence_digest, bundle_json) VALUES (?, ?, ?, ?)",
                    (
                        context.tenant_id,
                        context.workspace_id,
                        bundle.evidence.digest,
                        bundle.model_dump_json(),
                    ),
                )
        return len(bundles)
