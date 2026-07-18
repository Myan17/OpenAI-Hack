"""Privacy-minimized aggregate metrics for assurance rollout operations."""

from collections import Counter

from pydantic import BaseModel, ConfigDict


class AssuranceMetricsSnapshot(BaseModel):
    """Exportable aggregate counters that contain no prompts, payloads, or identities."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    counters: dict[str, int]


class AssuranceMetrics:
    """In-process aggregate counter; callers choose only fixed outcome names."""

    def __init__(self) -> None:
        self._counters: Counter[str] = Counter()

    def record(self, outcome: str) -> None:
        """Record one approved aggregate outcome label without attached user data."""

        if not outcome or ":" in outcome and outcome.split(":", 1)[0] not in {"report", "replay", "candidate"}:
            raise ValueError("metric outcome must be a supported aggregate label")
        self._counters[outcome] += 1

    def snapshot(self) -> AssuranceMetricsSnapshot:
        """Return stable JSON-ready counters for a local operator health surface."""

        return AssuranceMetricsSnapshot(counters=dict(sorted(self._counters.items())))
