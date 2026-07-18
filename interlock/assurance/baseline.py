"""Frozen local compatibility baseline for the existing deterministic demo path."""

import hashlib
import json
import time

from pydantic import BaseModel, ConfigDict, Field

from interlock.engine.models import Policy
from interlock.engine.simulator import SimulationResult, SimulationStep, developer_agent_trace, simulate


class BaselineRecord(BaseModel):
    """Versioned policy/trace fixture that must remain compatible with the demo."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    baseline_id: str = Field(min_length=1)
    policy: Policy
    steps: tuple[SimulationStep, ...]

    def canonical_json(self) -> str:
        """Return a stable fixture serialization for change-control reference."""

        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

    @property
    def digest(self) -> str:
        """Hash the exact policy and trace expected by the protected baseline."""

        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


class BaselineMeasurement(BaseModel):
    """Local timing observation used to catch material demo regressions over time."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    baseline_digest: str
    duration_ms: float = Field(ge=0)


def developer_agent_baseline() -> BaselineRecord:
    """Return the immutable local fixture for the safe-read/destructive-halt path."""

    return BaselineRecord(
        baseline_id="developer-agent-v1",
        policy=Policy(task="Inspect the staging schema.", allowed_tools={"inspect"}),
        steps=tuple(developer_agent_trace()),
    )


def verify_baseline(baseline: BaselineRecord) -> SimulationResult:
    """Replay the protected baseline through the existing pure no-effect simulator."""

    return simulate(baseline.policy, list(baseline.steps))


def measure_baseline(baseline: BaselineRecord) -> BaselineMeasurement:
    """Measure one local pure replay without putting a clock in the engine path."""

    started_ns = time.perf_counter_ns()
    verify_baseline(baseline)
    duration_ms = (time.perf_counter_ns() - started_ns) / 1_000_000
    return BaselineMeasurement(baseline_digest=baseline.digest, duration_ms=duration_ms)
