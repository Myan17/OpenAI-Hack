"""Additive SQLite persistence with mandatory tenant/workspace scope."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from interlock.assurance.tenancy import TenantContext, require_role


def _connect(db_path: Path) -> sqlite3.Connection:
    """Open a connection with SQLite referential-integrity enforcement enabled."""

    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


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
        with _connect(self._db_path) as connection:
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
        with _connect(self._db_path) as connection:
            cursor = connection.execute(
                "INSERT INTO tenant_assurance_cases (tenant_id, workspace_id, title, summary) VALUES (?, ?, ?, ?)",
                (context.tenant_id, context.workspace_id, title, summary),
            )
            case_id = int(cursor.lastrowid)
        return TenantCase(case_id, context.tenant_id, context.workspace_id, title, summary)

    def list(self, context: TenantContext) -> list[TenantCase]:
        with _connect(self._db_path) as connection:
            rows = connection.execute(
                "SELECT id, tenant_id, workspace_id, title, summary FROM tenant_assurance_cases WHERE tenant_id = ? AND workspace_id = ? ORDER BY id",
                (context.tenant_id, context.workspace_id),
            ).fetchall()
        return [TenantCase(int(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4])) for row in rows]

    def get(self, context: TenantContext, case_id: int) -> TenantCase | None:
        """Resolve one case only inside the caller's immutable tenant/workspace boundary."""

        with _connect(self._db_path) as connection:
            row = connection.execute(
                "SELECT id, tenant_id, workspace_id, title, summary FROM tenant_assurance_cases WHERE tenant_id = ? AND workspace_id = ? AND id = ?",
                (context.tenant_id, context.workspace_id, case_id),
            ).fetchone()
        if row is None:
            return None
        return TenantCase(int(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]))


class TenantRegistry:
    """Durable tenant/workspace/membership control-plane foundation."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with _connect(self._db_path) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS tenants (id TEXT PRIMARY KEY, status TEXT NOT NULL DEFAULT 'active')")
            connection.execute("CREATE TABLE IF NOT EXISTS workspaces (tenant_id TEXT NOT NULL, id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active', PRIMARY KEY (tenant_id, id), FOREIGN KEY (tenant_id) REFERENCES tenants(id))")
            connection.execute("CREATE TABLE IF NOT EXISTS memberships (tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL, subject_id TEXT NOT NULL, role TEXT NOT NULL, PRIMARY KEY (tenant_id, workspace_id, subject_id), FOREIGN KEY (tenant_id, workspace_id) REFERENCES workspaces(tenant_id, id))")
            tenant_columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(tenants)").fetchall()}
            workspace_columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(workspaces)").fetchall()}
            if "status" not in tenant_columns:
                connection.execute("ALTER TABLE tenants ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
            if "status" not in workspace_columns:
                connection.execute("ALTER TABLE workspaces ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")

    def create_tenant(self, tenant_id: str) -> None:
        with _connect(self._db_path) as connection:
            connection.execute("INSERT INTO tenants (id) VALUES (?)", (tenant_id,))

    def create_workspace(self, tenant_id: str, workspace_id: str) -> None:
        with _connect(self._db_path) as connection:
            connection.execute("INSERT INTO workspaces (tenant_id, id) VALUES (?, ?)", (tenant_id, workspace_id))

    def add_membership(self, tenant_id: str, workspace_id: str, subject_id: str, role: str) -> None:
        TenantContext(tenant_id=tenant_id, workspace_id=workspace_id, subject_id=subject_id, role=role)
        with _connect(self._db_path) as connection:
            connection.execute("INSERT INTO memberships (tenant_id, workspace_id, subject_id, role) VALUES (?, ?, ?, ?)", (tenant_id, workspace_id, subject_id, role))

    def set_tenant_status(self, tenant_id: str, status: str) -> None:
        self._set_status("tenants", "id = ?", (tenant_id,), status)

    def set_workspace_status(self, tenant_id: str, workspace_id: str, status: str) -> None:
        self._set_status("workspaces", "tenant_id = ? AND id = ?", (tenant_id, workspace_id), status)

    def context_for(self, subject_id: str, tenant_id: str, workspace_id: str) -> TenantContext | None:
        with sqlite3.connect(self._db_path) as connection:
            row = connection.execute(
                """SELECT memberships.role FROM memberships
                JOIN tenants ON tenants.id = memberships.tenant_id AND tenants.status = 'active'
                JOIN workspaces ON workspaces.tenant_id = memberships.tenant_id
                    AND workspaces.id = memberships.workspace_id AND workspaces.status = 'active'
                WHERE memberships.subject_id = ? AND memberships.tenant_id = ? AND memberships.workspace_id = ?""",
                (subject_id, tenant_id, workspace_id),
            ).fetchone()
        return None if row is None else TenantContext(tenant_id=tenant_id, workspace_id=workspace_id, subject_id=subject_id, role=str(row[0]))

    def _set_status(self, table: str, predicate: str, values: tuple[str, ...], status: str) -> None:
        if status not in {"active", "suspended"}:
            raise ValueError("tenant lifecycle status must be active or suspended")
        with _connect(self._db_path) as connection:
            cursor = connection.execute(f"UPDATE {table} SET status = ? WHERE {predicate}", (status, *values))
        if cursor.rowcount != 1:
            raise ValueError("tenant lifecycle target does not exist")
