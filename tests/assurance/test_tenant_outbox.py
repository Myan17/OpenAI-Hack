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


def test_outbox_quarantines_after_bounded_local_retry_failures(tmp_path) -> None:
    outbox = TenantOutbox(tmp_path / "outbox.sqlite")
    context = TenantContext(tenant_id="acme", workspace_id="prod", subject_id="service", role="service")
    receipt = outbox.enqueue(context, idempotency_key="key-1", payload_digest="a" * 64)

    retrying = outbox.record_failure(context, receipt.receipt_id, failure_class="unavailable", max_attempts=2)
    quarantined = outbox.record_failure(context, receipt.receipt_id, failure_class="unavailable", max_attempts=2)

    assert retrying is not None and (retrying.status, retrying.attempt_count, retrying.failure_class) == ("pending", 1, "unavailable")
    assert quarantined is not None and (quarantined.status, quarantined.attempt_count, quarantined.failure_class) == ("dead_letter", 2, "unavailable")
    assert outbox.pending(context) == []
    assert outbox.dead_letters(context) == [quarantined]
