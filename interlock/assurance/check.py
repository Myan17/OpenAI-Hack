"""GitHub-Check-compatible advisory payloads built without a GitHub dependency."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from interlock.assurance.models import ReleaseEvidenceBundle


class AdvisoryCheck(BaseModel):
    """Portable check payload that a future GitHub adapter can submit unchanged."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    conclusion: Literal["success", "action_required", "neutral"]
    advisory: bool
    summary: str
    details: tuple[str, ...]
    evidence_digest: str


def build_advisory_check(bundle: ReleaseEvidenceBundle) -> AdvisoryCheck:
    """Map a verified local verdict to a human-reviewable, non-blocking check payload."""

    conclusion = {
        "pass": "success",
        "fail": "action_required",
        "inconclusive": "neutral",
    }[bundle.verdict]
    details = _details(bundle)
    return AdvisoryCheck(
        name="Developer-Agent Change Control",
        conclusion=conclusion,
        advisory=True,
        summary=f"Advisory assurance verdict: {bundle.verdict}. Evidence: {bundle.digest}",
        details=details,
        evidence_digest=bundle.digest,
    )


def _details(bundle: ReleaseEvidenceBundle) -> tuple[str, ...]:
    """Return stable explanations based only on the typed evidence bundle."""

    details: list[str] = [f"authority_expansion={bundle.delta.has_expansion}"]
    details.extend(
        f"case:{replay.case_id}={'pass' if replay.passed else 'fail'}" for replay in bundle.replays
    )
    return tuple(details)
