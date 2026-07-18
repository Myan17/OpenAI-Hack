"""Compatibility baseline tests for the existing demo and pure simulator."""

from interlock.assurance.baseline import developer_agent_baseline, measure_baseline, verify_baseline


def test_developer_agent_baseline_is_digest_stable_and_replays_without_misses() -> None:
    baseline = developer_agent_baseline()

    result = verify_baseline(baseline)

    assert baseline.digest == developer_agent_baseline().digest
    assert result.metrics.missed_unsafe == 0
    assert result.metrics.blocked_safe == 0


def test_baseline_measurement_records_a_nonnegative_local_duration() -> None:
    measurement = measure_baseline(developer_agent_baseline())

    assert measurement.duration_ms >= 0
    assert measurement.baseline_digest == developer_agent_baseline().digest
