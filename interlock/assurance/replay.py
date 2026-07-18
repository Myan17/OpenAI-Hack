"""Effect-free regression replay backed by the existing pure policy simulator."""

from interlock.assurance.models import ReplayCaseResult
from interlock.engine.models import Policy
from interlock.engine.simulator import SimulationStep, simulate


def replay_case(*, case_id: int, policy: Policy, steps: list[SimulationStep]) -> ReplayCaseResult:
    """Replay one labeled case without models, adapters, network, or dispatch."""

    result = simulate(policy, steps)
    metrics = result.metrics
    return ReplayCaseResult(
        case_id=case_id,
        passed=metrics.blocked_safe == 0 and metrics.missed_unsafe == 0,
        allowed_safe=metrics.allowed_safe,
        blocked_safe=metrics.blocked_safe,
        stopped_unsafe=metrics.stopped_unsafe,
        missed_unsafe=metrics.missed_unsafe,
        step_decisions=tuple(item.verdict.decision.value for item in result.results),
    )
