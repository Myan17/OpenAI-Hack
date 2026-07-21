"""Tenant observability records aggregate outcomes without tenant identifiers."""

from interlock.assurance.metrics import AssuranceMetrics
from interlock.assurance.tenant_metrics import TenantSafeMetrics
from interlock.assurance.tenancy import TenantContext


def test_tenant_safe_metrics_aggregate_without_scope_or_evidence_data() -> None:
    aggregate = AssuranceMetrics()
    metrics = TenantSafeMetrics(aggregate)
    context = TenantContext(
        tenant_id="secret-tenant", workspace_id="secret-workspace",
        subject_id="secret-subject", role="service",
    )

    metrics.record_callback_outcome(context, "delivered")
    metrics.record_callback_outcome(context, "delivered")

    assert aggregate.snapshot().counters == {"tenant:callback_delivered": 2}
