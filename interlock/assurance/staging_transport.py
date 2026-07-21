"""Fixture-only advisory transport boundary for future staging integration."""

from dataclasses import dataclass
from typing import Literal, Protocol

from interlock.assurance.models import AdvisoryCallback
from interlock.assurance.tenant_outbox import CallbackReceipt, TenantOutbox
from interlock.assurance.tenancy import TenantContext, require_role


DeliveryStatus = Literal["delivered", "duplicate", "unavailable", "invalid"]


@dataclass(frozen=True)
class DeliveryResult:
    status: DeliveryStatus
    idempotency_key: str


@dataclass(frozen=True)
class FixtureDeliveryAttempt:
    tenant_id: str
    workspace_id: str
    idempotency_key: str
    evidence_digest: str


class AdvisoryTransport(Protocol):
    """Minimal protocol a separately authorized staging transport must implement."""

    def dispatch(
        self, context: TenantContext, callback: AdvisoryCallback, *, idempotency_key: str
    ) -> DeliveryResult: ...


class FixtureAdvisoryTransport:
    """In-memory test double; it deliberately cannot communicate outside this process."""

    def __init__(self, *, available: bool = True) -> None:
        self._available = available
        self._attempts: list[FixtureDeliveryAttempt] = []
        self._delivered: set[tuple[str, str, str]] = set()

    @property
    def attempts(self) -> tuple[FixtureDeliveryAttempt, ...]:
        return tuple(self._attempts)

    def dispatch(
        self, context: TenantContext, callback: AdvisoryCallback, *, idempotency_key: str
    ) -> DeliveryResult:
        require_role(context, "service", "tenant_admin")
        if not idempotency_key:
            return DeliveryResult("invalid", idempotency_key)
        if not self._available:
            return DeliveryResult("unavailable", idempotency_key)
        key = (context.tenant_id, context.workspace_id, idempotency_key)
        if key in self._delivered:
            return DeliveryResult("duplicate", idempotency_key)
        self._delivered.add(key)
        self._attempts.append(
            FixtureDeliveryAttempt(
                tenant_id=context.tenant_id,
                workspace_id=context.workspace_id,
                idempotency_key=idempotency_key,
                evidence_digest=callback.evidence_digest,
            )
        )
        return DeliveryResult("delivered", idempotency_key)


class FixtureCallbackWorker:
    """Local-only worker boundary that fails closed before a future transport call."""

    def __init__(self, outbox: TenantOutbox, transport: AdvisoryTransport) -> None:
        self._outbox = outbox
        self._transport = transport

    def process(
        self, context: TenantContext, receipt: CallbackReceipt, callback: AdvisoryCallback
    ) -> DeliveryResult:
        require_role(context, "service", "tenant_admin")
        if (
            receipt.tenant_id != context.tenant_id
            or receipt.workspace_id != context.workspace_id
            or receipt.status != "pending"
            or receipt.payload_digest != callback.evidence_digest
        ):
            return DeliveryResult("invalid", receipt.idempotency_key)
        result = self._transport.dispatch(
            context, callback, idempotency_key=receipt.idempotency_key
        )
        if result.status in {"delivered", "duplicate"}:
            self._outbox.mark_delivered(context, receipt.receipt_id)
        return result
