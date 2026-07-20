"""Tenant-scoped callback receipts are idempotent and never dispatch externally."""

from interlock.assurance.tenant_outbox import TenantOutbox
from interlock.assurance.tenancy import TenantContext


def test_outbox_deduplicates_callback_receipts_within_one_workspace(tmp_path) -> None:
    outbox = TenantOutbox(tmp_path / "outbox.sqlite")
    context = TenantContext(tenant_id="acme", workspace_id="prod", subject_id="service", role="service")

    first = outbox.enqueue(context, idempotency_key="key-1", payload_digest="a" * 64)
    duplicate = outbox.enqueue(context, idempotency_key="key-1", payload_digest="a" * 64)

    assert first.receipt_id == duplicate.receipt_id
    assert outbox.pending(context) == [first]
