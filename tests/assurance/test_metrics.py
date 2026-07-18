"""Tests for privacy-minimized operational counters."""

from interlock.assurance.metrics import AssuranceMetrics


def test_metrics_track_only_aggregate_named_outcomes() -> None:
    metrics = AssuranceMetrics()

    metrics.record("authority_diff")
    metrics.record("report:pass")
    metrics.record("report:pass")

    snapshot = metrics.snapshot()

    assert snapshot.counters == {"authority_diff": 1, "report:pass": 2}
