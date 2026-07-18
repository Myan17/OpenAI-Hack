"""Tests for effect-free assurance replay over the existing pure simulator."""

from interlock.assurance.replay import replay_case
from interlock.engine.models import DbAction, DbArgs, EnforcementContext, InspectAction, InspectArgs, Policy
from interlock.engine.simulator import SimulationStep


def test_replay_case_passes_when_safe_work_flows_and_unsafe_work_stops() -> None:
    result = replay_case(
        case_id=7,
        policy=Policy(task="inspect", allowed_tools={"inspect"}),
        steps=[
            SimulationStep(
                id="read",
                description="Read ledger.",
                expected_safe=True,
                action=InspectAction(args=InspectArgs(resource="ledger")),
                context=EnforcementContext(),
            ),
            SimulationStep(
                id="drop",
                description="Drop users.",
                expected_safe=False,
                action=DbAction(args=DbArgs(sql="DROP TABLE users")),
                context=EnforcementContext(),
            ),
        ],
    )

    assert result.passed is True
    assert result.missed_unsafe == 0
    assert result.blocked_safe == 0


def test_replay_case_fails_when_an_unsafe_action_is_allowed() -> None:
    result = replay_case(
        case_id=8,
        policy=Policy(task="inspect", allowed_tools={"inspect"}),
        steps=[
            SimulationStep(
                id="incorrectly-safe",
                description="A flawed label verifies regression detection.",
                expected_safe=False,
                action=InspectAction(args=InspectArgs(resource="ledger")),
                context=EnforcementContext(),
            )
        ],
    )

    assert result.passed is False
    assert result.missed_unsafe == 1
