"""Local staging transport tests: no endpoint, network, or credentials are involved."""

from interlock.assurance.models import AdvisoryCallback
from interlock.assurance.staging_transport import FixtureAdvisoryTransport, FixtureCallbackWorker
from interlock.assurance.tenant_outbox import TenantOutbox
from interlock.assurance.tenancy import TenantContext


def _context() -> TenantContext:
    return TenantContext(tenant_id="acme", workspace_id="staging", subject_id="worker", role="service")


def _callback(digest: str = "a" * 64) -> AdvisoryCallback:
    return AdvisoryCallback(
        correlation_id="corr-1", verdict="pass", action="continue_advisory",
        reason_codes=("evidence_verified",), evidence_digest=digest, replay_case_ids=(1,),
    )


def test_fixture_worker_delivers_once_and_marks_the_local_outbox(tmp_path) -> None:
    context = _context()
    outbox = TenantOutbox(tmp_path / "outbox.sqlite")
    receipt = outbox.enqueue(context, idempotency_key="corr-1", payload_digest="a" * 64)
    transport = FixtureAdvisoryTransport()

    result = FixtureCallbackWorker(outbox, transport, callback_enabled=True).process(context, receipt, _callback())

    assert result.status == "delivered"
    assert outbox.pending(context) == []
    assert len(transport.attempts) == 1


def test_fixture_worker_fails_closed_for_unavailable_duplicate_and_invalid_work(tmp_path) -> None:
    context = _context()
    outbox = TenantOutbox(tmp_path / "outbox.sqlite")
    receipt = outbox.enqueue(context, idempotency_key="corr-1", payload_digest="a" * 64)
    transport = FixtureAdvisoryTransport(available=False)
    worker = FixtureCallbackWorker(outbox, transport, callback_enabled=True)

    unavailable = worker.process(context, receipt, _callback())
    invalid = worker.process(context, receipt, _callback("b" * 64))

    assert unavailable.status == "unavailable"
    assert invalid.status == "invalid"
    assert outbox.pending(context) == [receipt]
    assert transport.attempts == ()

    duplicate_transport = FixtureAdvisoryTransport()
    first = duplicate_transport.dispatch(context, _callback(), idempotency_key="corr-1")
    duplicate = duplicate_transport.dispatch(context, _callback(), idempotency_key="corr-1")
    assert (first.status, duplicate.status) == ("delivered", "duplicate")


def test_fixture_worker_is_disabled_by_default_without_touching_the_outbox(tmp_path) -> None:
    context = _context()
    outbox = TenantOutbox(tmp_path / "outbox.sqlite")
    receipt = outbox.enqueue(context, idempotency_key="corr-1", payload_digest="a" * 64)
    transport = FixtureAdvisoryTransport()

    result = FixtureCallbackWorker(outbox, transport).process(context, receipt, _callback())

    assert result.status == "disabled"
    assert outbox.pending(context) == [receipt]
    assert transport.attempts == ()
