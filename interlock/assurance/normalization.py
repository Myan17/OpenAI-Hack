"""Adapter-neutral trace records for future MCP, OpenTelemetry, and CI imports."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from interlock.engine.simulator import SimulationStep


class NormalizedTraceStep(BaseModel):
    """Provider-neutral typed action and context captured without tool dispatch."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    step_id: str = Field(min_length=1)
    expected_safe: bool
    action: dict[str, Any]
    context: dict[str, Any]


class NormalizedTrace(BaseModel):
    """A versioned portable trace envelope used by adapter conformance tests."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    source: str = Field(min_length=1)
    steps: tuple[NormalizedTraceStep, ...]


def normalize_steps(*, source: str, steps: list[SimulationStep]) -> NormalizedTrace:
    """Normalize existing typed simulator steps without importing an external provider SDK."""

    return NormalizedTrace(
        source=source,
        steps=tuple(
            NormalizedTraceStep(
                step_id=step.id,
                expected_safe=step.expected_safe,
                action=step.action.model_dump(mode="json"),
                context=step.context.model_dump(mode="json"),
            )
            for step in steps
        ),
    )


def validate_normalized_trace(trace: NormalizedTrace) -> bool:
    """Check the minimum conformance invariants without provider-specific assumptions."""

    return (
        trace.schema_version == 1
        and bool(trace.source)
        and all(step.step_id and "tool" in step.action and "args" in step.action for step in trace.steps)
    )
