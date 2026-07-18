"""Tests for repeat-trial classification without false certainty."""

from interlock.assurance.models import ReplayCaseResult
from interlock.assurance.trials import classify_trials


def test_all_passing_trials_are_a_pass() -> None:
    aggregate = classify_trials(
        4,
        [ReplayCaseResult(case_id=4, passed=True), ReplayCaseResult(case_id=4, passed=True)],
    )

    assert aggregate.verdict == "pass"
    assert aggregate.trial_count == 2


def test_all_failing_trials_are_a_fail() -> None:
    aggregate = classify_trials(
        5,
        [ReplayCaseResult(case_id=5, passed=False), ReplayCaseResult(case_id=5, passed=False)],
    )

    assert aggregate.verdict == "fail"


def test_mixed_trials_are_inconclusive_not_a_false_pass() -> None:
    aggregate = classify_trials(
        6,
        [ReplayCaseResult(case_id=6, passed=True), ReplayCaseResult(case_id=6, passed=False)],
    )

    assert aggregate.verdict == "inconclusive"
