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


def test_outbox_keeps_idempotency_and_completion_within_tenant_scope(tmp_path) -> None:
    outbox = TenantOutbox(tmp_path / "outbox.sqlite")
    acme = TenantContext(tenant_id="acme", workspace_id="prod", subject_id="service", role="service")
    bravo = TenantContext(tenant_id="bravo", workspace_id="prod", subject_id="service", role="service")

    acme_receipt = outbox.enqueue(acme, idempotency_key="key-1", payload_digest="a" * 64)
    bravo_receipt = outbox.enqueue(bravo, idempotency_key="key-1", payload_digest="b" * 64)

    assert acme_receipt.receipt_id != bravo_receipt.receipt_id
    assert outbox.mark_delivered(bravo, acme_receipt.receipt_id) is None
    delivered = outbox.mark_delivered(acme, acme_receipt.receipt_id)

    assert delivered is not None and delivered.status == "delivered"
    assert outbox.pending(acme) == []
    assert outbox.pending(bravo) == [bravo_receipt]
