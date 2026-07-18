"""Tests for adapter-neutral normalized traces built from typed simulator steps."""

from interlock.assurance.normalization import normalize_steps, validate_normalized_trace
from interlock.engine.models import EnforcementContext, InspectAction, InspectArgs
from interlock.engine.simulator import SimulationStep


def test_normalized_trace_is_stable_and_validates_required_provenance() -> None:
    trace = normalize_steps(
        source="engine-simulator",
        steps=[
            SimulationStep(
                id="read-ledger",
                description="Read local ledger.",
                expected_safe=True,
                action=InspectAction(args=InspectArgs(resource="ledger")),
                context=EnforcementContext(),
            )
        ],
    )

    assert trace.source == "engine-simulator"
    assert trace.steps[0].action["tool"] == "inspect"
    assert validate_normalized_trace(trace) is True
