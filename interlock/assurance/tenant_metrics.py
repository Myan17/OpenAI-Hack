"""Privacy-minimized tenant outcome aggregation."""

from interlock.assurance.metrics import AssuranceMetrics
from interlock.assurance.tenancy import TenantContext, tenant_metric_key


class TenantSafeMetrics:
    """Record fixed operational outcomes without emitting tenant scope values."""

    def __init__(self, aggregate: AssuranceMetrics) -> None:
        self._aggregate = aggregate

    def record_callback_outcome(self, context: TenantContext, outcome: str) -> None:
        """Record an aggregate callback outcome; context is intentionally discarded."""

        if outcome not in {"delivered", "duplicate", "unavailable", "invalid", "disabled"}:
            raise ValueError("unsupported tenant callback outcome")
        self._aggregate.record(tenant_metric_key(context, f"callback_{outcome}"))
