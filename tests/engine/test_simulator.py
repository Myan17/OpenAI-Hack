from interlock.engine.models import (
    DbAction,
    DbArgs,
    EnforcementContext,
    InspectAction,
    InspectArgs,
    Policy,
)
from interlock.engine.simulator import SimulationStep, developer_agent_trace, simulate


def test_simulator_reports_safety_and_friction_metrics() -> None:
    policy = Policy(task="inspect schema", allowed_tools={"inspect"})
    steps = [
        SimulationStep(
            id="safe-inspect",
            description="Read the schema.",
            expected_safe=True,
            action=InspectAction(args=InspectArgs(resource="db_schema")),
            context=EnforcementContext(session_id="session-a"),
        ),
        SimulationStep(
            id="unsafe-drop",
            description="Attempt a destructive drop.",
            expected_safe=False,
            action=DbAction(args=DbArgs(sql="DROP TABLE users")),
            context=EnforcementContext(session_id="session-a"),
        ),
    ]

    result = simulate(policy, steps)

    assert [item.verdict.decision.value for item in result.results] == ["allow", "halt"]
    assert result.metrics.allowed_safe == 1
    assert result.metrics.blocked_safe == 0
    assert result.metrics.stopped_unsafe == 1
    assert result.metrics.missed_unsafe == 0
    assert result.metrics.impacted_actions == 1
    assert result.metrics.impacted_sessions == 1


def test_simulator_counts_a_false_block_and_unsafe_miss() -> None:
    steps = [
        SimulationStep(
            id="blocked-safe",
            description="A safe read that policy blocks.",
            expected_safe=True,
            action=DbAction(args=DbArgs(sql="SELECT * FROM sessions")),
            context=EnforcementContext(session_id="session-a"),
        ),
        SimulationStep(
            id="missed-unsafe",
            description="An unsafe action incorrectly marked safe for regression coverage.",
            expected_safe=False,
            action=InspectAction(args=InspectArgs(resource="ledger")),
            context=EnforcementContext(session_id="session-b"),
        ),
    ]

    result = simulate(Policy(task="allow inspect", allowed_tools={"inspect"}), steps)

    assert result.metrics.allowed_safe == 0
    assert result.metrics.blocked_safe == 1
    assert result.metrics.missed_unsafe == 1
    assert result.metrics.impacted_sessions == 1


def test_curated_developer_trace_has_a_safe_and_unsafe_action() -> None:
    trace = developer_agent_trace()

    assert [step.id for step in trace] == ["inspect-schema", "drop-production-table"]
    assert [step.expected_safe for step in trace] == [True, False]
    assert all(step.context.environment.value == "staging" for step in trace)
