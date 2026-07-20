"""Additive SQLite persistence with mandatory tenant/workspace scope."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from interlock.assurance.tenancy import TenantContext, require_role


@dataclass(frozen=True)
class TenantCase:
    case_id: int
    tenant_id: str
    workspace_id: str
    title: str
    summary: str


class TenantCaseStore:
    """Minimal scoped persistence foundation; no unscoped read or write API exists."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS tenant_assurance_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                UNIQUE (tenant_id, workspace_id, id))"""
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_tenant_cases_scope ON tenant_assurance_cases (tenant_id, workspace_id, id)")

    def create(self, context: TenantContext, *, title: str, summary: str) -> TenantCase:
        require_role(context, "tenant_admin", "assurance_reviewer", "developer")
        if not title or not summary:
            raise ValueError("tenant case title and summary are required")
        with sqlite3.connect(self._db_path) as connection:
            cursor = connection.execute(
                "INSERT INTO tenant_assurance_cases (tenant_id, workspace_id, title, summary) VALUES (?, ?, ?, ?)",
                (context.tenant_id, context.workspace_id, title, summary),
            )
            case_id = int(cursor.lastrowid)
        return TenantCase(case_id, context.tenant_id, context.workspace_id, title, summary)

    def list(self, context: TenantContext) -> list[TenantCase]:
        with sqlite3.connect(self._db_path) as connection:
            rows = connection.execute(
                "SELECT id, tenant_id, workspace_id, title, summary FROM tenant_assurance_cases WHERE tenant_id = ? AND workspace_id = ? ORDER BY id",
                (context.tenant_id, context.workspace_id),
            ).fetchall()
        return [TenantCase(int(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4])) for row in rows]

    def get(self, context: TenantContext, case_id: int) -> TenantCase | None:
        """Resolve one case only inside the caller's immutable tenant/workspace boundary."""

        with sqlite3.connect(self._db_path) as connection:
            row = connection.execute(
                "SELECT id, tenant_id, workspace_id, title, summary FROM tenant_assurance_cases WHERE tenant_id = ? AND workspace_id = ? AND id = ?",
                (context.tenant_id, context.workspace_id, case_id),
            ).fetchone()
        if row is None:
            return None
        return TenantCase(int(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]))
