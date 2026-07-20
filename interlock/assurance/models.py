"""Strict, canonical data contracts for developer-agent change control."""

import hashlib
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


_DIGEST_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def _ordered_unique(values: object) -> tuple[str, ...]:
    """Normalize a collection of authority labels into a stable tuple."""

    if values is None:
        return ()
    if not isinstance(values, (list, tuple, set, frozenset)):
        raise TypeError("authority values must be a collection of strings")
    if not all(isinstance(value, str) and value for value in values):
        raise ValueError("authority values must be non-empty strings")
    return tuple(sorted(set(values)))


class AuthoritySurface(BaseModel):
    """Canonical capability view used for semantic release comparisons."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    principals: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    filesystem_roots: tuple[str, ...] = ()
    db_operations: tuple[str, ...] = ()
    db_tables: tuple[str, ...] = ()
    github_operations: tuple[str, ...] = ()
    github_repositories: tuple[str, ...] = ()
    environments: tuple[str, ...] = ()
    unrestricted_dimensions: tuple[str, ...] = ()
    spend_cap_cents: int = Field(default=0, ge=0)
    irreversible_actions_require_approval: bool = True

    @field_validator(
        "principals",
        "tools",
        "filesystem_roots",
        "db_operations",
        "db_tables",
        "github_operations",
        "github_repositories",
        "environments",
        "unrestricted_dimensions",
        mode="before",
    )
    @classmethod
    def normalize_authority_values(cls, values: object) -> tuple[str, ...]:
        """Reject ambiguous labels and make unordered inputs deterministic."""

        return _ordered_unique(values)


class ChangeManifest(BaseModel):
    """Versioned, tamper-evident input record for a release comparison."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    release_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    captured_at_epoch: int = Field(default=0, ge=0)
    components: dict[str, str] = Field(default_factory=dict)
    authority: AuthoritySurface = Field(default_factory=AuthoritySurface)

    @field_validator("components")
    @classmethod
    def validate_component_digests(cls, components: dict[str, str]) -> dict[str, str]:
        """Require named SHA-256 digests rather than mutable component references."""

        for name, digest in components.items():
            if not name or not _DIGEST_PATTERN.fullmatch(digest):
                raise ValueError("components must map non-empty names to lowercase SHA-256 digests")
        return dict(sorted(components.items()))

    def canonical_json(self) -> str:
        """Return a stable serialization used as the local evidence input."""

        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

    @property
    def digest(self) -> str:
        """Return the SHA-256 digest of the canonical manifest serialization."""

        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


class ProposedChangeEnvelope(BaseModel):
    """Strict, fixture-only orchestration input that contains no prompt or source payload."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    correlation_id: str = Field(min_length=1, max_length=128)
    source_system: Literal["multica-fixture"] = "multica-fixture"
    task_id: str = Field(min_length=1, max_length=128)
    run_id: str = Field(min_length=1, max_length=128)
    change_class: Literal["code_change", "policy_change", "skill_admission", "adapter_change"]
    components: dict[str, str] = Field(default_factory=dict)
    authority: AuthoritySurface = Field(default_factory=AuthoritySurface)
    provenance: Literal["fixture"] = "fixture"

    @field_validator("components")
    @classmethod
    def validate_components(cls, components: dict[str, str]) -> dict[str, str]:
        """Reuse the manifest's digest discipline for adapter-provided references."""

        return ChangeManifest.validate_component_digests(components)

    def canonical_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


class AdvisoryCallback(BaseModel):
    """Minimum safe result for an external task timeline; never includes raw agent data."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    correlation_id: str = Field(min_length=1, max_length=128)
    verdict: Literal["pass", "fail", "inconclusive"]
    action: Literal["continue_advisory", "reviewer_required", "quarantine"]
    reason_codes: tuple[str, ...] = ()
    evidence_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    replay_case_ids: tuple[int, ...] = ()

    @field_validator("reason_codes", mode="before")
    @classmethod
    def normalize_reason_codes(cls, values: object) -> tuple[str, ...]:
        return _ordered_unique(values)


class AuthorityDelta(BaseModel):
    """Semantic before/after authority changes, separate from raw configuration text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    added_principals: tuple[str, ...] = ()
    removed_principals: tuple[str, ...] = ()
    added_tools: tuple[str, ...] = ()
    removed_tools: tuple[str, ...] = ()
    added_filesystem_roots: tuple[str, ...] = ()
    removed_filesystem_roots: tuple[str, ...] = ()
    added_db_operations: tuple[str, ...] = ()
    removed_db_operations: tuple[str, ...] = ()
    added_db_tables: tuple[str, ...] = ()
    removed_db_tables: tuple[str, ...] = ()
    added_github_operations: tuple[str, ...] = ()
    removed_github_operations: tuple[str, ...] = ()
    added_github_repositories: tuple[str, ...] = ()
    removed_github_repositories: tuple[str, ...] = ()
    added_environments: tuple[str, ...] = ()
    removed_environments: tuple[str, ...] = ()
    spend_cap_increase_cents: int = Field(default=0, ge=0)
    approval_requirement_removed: bool = False

    @property
    def has_expansion(self) -> bool:
        """Whether a candidate release can perform anything newly consequential."""

        return any(
            (
                self.added_principals,
                self.added_tools,
                self.added_filesystem_roots,
                self.added_db_operations,
                self.added_db_tables,
                self.added_github_operations,
                self.added_github_repositories,
                self.added_environments,
                self.spend_cap_increase_cents > 0,
                self.approval_requirement_removed,
            )
        )


class SandboxSnapshot(BaseModel):
    """Minimal local state evidence collected from the contained demo sandbox."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ledger_balance_cents: int = Field(ge=0)
    session_count: int = Field(ge=0)
    file_paths: tuple[str, ...] = ()

    @field_validator("file_paths", mode="before")
    @classmethod
    def normalize_file_paths(cls, values: object) -> tuple[str, ...]:
        """Keep snapshots stable regardless of filesystem enumeration order."""

        return _ordered_unique(values)


class EffectContract(BaseModel):
    """Hard, sandbox-state assertions for release replay evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: str = Field(min_length=1)
    expected_ledger_balance_cents: int | None = Field(default=None, ge=0)
    expected_session_count: int | None = Field(default=None, ge=0)
    forbidden_file_paths: tuple[str, ...] = ()

    @field_validator("forbidden_file_paths", mode="before")
    @classmethod
    def normalize_forbidden_file_paths(cls, values: object) -> tuple[str, ...]:
        """Reject ambiguous forbidden-file assertions."""

        return _ordered_unique(values)


class EffectEvaluation(BaseModel):
    """Deterministic result for one effect-contract evaluation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: str
    passed: bool
    violations: tuple[str, ...] = ()
    observed: SandboxSnapshot


class AssuranceCase(BaseModel):
    """A redacted, reviewer-governed regression case stored outside policy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: int = Field(ge=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    source: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    status: Literal["pending_review", "active", "rejected", "expired", "retired", "revoked"]
    reviewer: str | None = None
    expires_at_epoch: int | None = Field(default=None, ge=0)


class ReplayCaseResult(BaseModel):
    """Stable summary of one effect-free regression replay."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: int = Field(ge=1)
    passed: bool
    allowed_safe: int = Field(default=0, ge=0)
    blocked_safe: int = Field(default=0, ge=0)
    stopped_unsafe: int = Field(default=0, ge=0)
    missed_unsafe: int = Field(default=0, ge=0)
    step_decisions: tuple[str, ...] = ()


class ReplayTrialAggregate(BaseModel):
    """Repeat-trial result that preserves uncertainty from non-deterministic paths."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: int = Field(ge=1)
    trial_count: int = Field(ge=1)
    verdict: Literal["pass", "fail", "inconclusive"]
    trials: tuple[ReplayCaseResult, ...]


class ReleaseEvidenceBundle(BaseModel):
    """Portable report-only evidence for one proposed developer-agent release."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    baseline: ChangeManifest
    candidate: ChangeManifest
    delta: AuthorityDelta
    replays: tuple[ReplayCaseResult, ...] = ()
    verdict: Literal["pass", "fail", "inconclusive"]
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")

    def canonical_json_without_digest(self) -> str:
        """Serialize immutable evidence fields for independent digest verification."""

        return json.dumps(
            self.model_dump(mode="json", exclude={"digest"}),
            sort_keys=True,
            separators=(",", ":"),
        )
