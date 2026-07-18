"""Repeat-trial aggregation for assurance paths that may become non-deterministic."""

from interlock.assurance.models import ReplayCaseResult, ReplayTrialAggregate


def classify_trials(case_id: int, trials: list[ReplayCaseResult]) -> ReplayTrialAggregate:
    """Classify unanimous results; mixed evidence is explicitly inconclusive."""

    if not trials:
        raise ValueError("at least one replay trial is required")
    if any(trial.case_id != case_id for trial in trials):
        raise ValueError("all replay trials must belong to the requested case")
    outcomes = {trial.passed for trial in trials}
    verdict = "pass" if outcomes == {True} else "fail" if outcomes == {False} else "inconclusive"
    return ReplayTrialAggregate(
        case_id=case_id,
        trial_count=len(trials),
        verdict=verdict,
        trials=tuple(trials),
    )
