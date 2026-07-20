"""Tenant-scoped durable callback receipts; deliberately no network delivery code."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from interlock.assurance.tenancy import TenantContext, require_role


@dataclass(frozen=True)
class CallbackReceipt:
    receipt_id: int
    tenant_id: str
    workspace_id: str
    idempotency_key: str
    payload_digest: str
    status: str


class TenantOutbox:
    """Store future staging callback work with tenant/workspace idempotency."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS tenant_callback_outbox (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL, idempotency_key TEXT NOT NULL, payload_digest TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', UNIQUE (tenant_id, workspace_id, idempotency_key))")

    def enqueue(self, context: TenantContext, *, idempotency_key: str, payload_digest: str) -> CallbackReceipt:
        require_role(context, "service", "tenant_admin")
        if not idempotency_key or len(payload_digest) != 64:
            raise ValueError("callback idempotency key and SHA-256 digest are required")
        with sqlite3.connect(self._db_path) as connection:
            connection.execute("INSERT OR IGNORE INTO tenant_callback_outbox (tenant_id, workspace_id, idempotency_key, payload_digest) VALUES (?, ?, ?, ?)", (context.tenant_id, context.workspace_id, idempotency_key, payload_digest))
            row = connection.execute("SELECT id, tenant_id, workspace_id, idempotency_key, payload_digest, status FROM tenant_callback_outbox WHERE tenant_id = ? AND workspace_id = ? AND idempotency_key = ?", (context.tenant_id, context.workspace_id, idempotency_key)).fetchone()
        return CallbackReceipt(int(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]), str(row[5]))

    def pending(self, context: TenantContext) -> list[CallbackReceipt]:
        require_role(context, "service", "tenant_admin")
        with sqlite3.connect(self._db_path) as connection:
            rows = connection.execute("SELECT id, tenant_id, workspace_id, idempotency_key, payload_digest, status FROM tenant_callback_outbox WHERE tenant_id = ? AND workspace_id = ? AND status = 'pending' ORDER BY id", (context.tenant_id, context.workspace_id)).fetchall()
        return [CallbackReceipt(int(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]), str(row[5])) for row in rows]

    def mark_delivered(self, context: TenantContext, receipt_id: int) -> CallbackReceipt | None:
        """Record a local completion only for a pending receipt inside this scope.

        Delivery is intentionally performed by no code in this repository; a future
        staging transport must explicitly report its result through this boundary.
        """

        require_role(context, "service", "tenant_admin")
        with sqlite3.connect(self._db_path) as connection:
            connection.execute(
                "UPDATE tenant_callback_outbox SET status = 'delivered' WHERE id = ? AND tenant_id = ? AND workspace_id = ? AND status = 'pending'",
                (receipt_id, context.tenant_id, context.workspace_id),
            )
            row = connection.execute(
                "SELECT id, tenant_id, workspace_id, idempotency_key, payload_digest, status FROM tenant_callback_outbox WHERE id = ? AND tenant_id = ? AND workspace_id = ? AND status = 'delivered'",
                (receipt_id, context.tenant_id, context.workspace_id),
            ).fetchone()
        if row is None:
            return None
        return CallbackReceipt(int(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]), str(row[5]))
