"""Typed, deterministic data contracts for Interlock's enforcement engine."""

from enum import Enum
from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field


class Reversibility(str, Enum):
    """Whether a concrete proposed action can be safely undone."""

    REVERSIBLE = "reversible"
    IRREVERSIBLE = "irreversible"
    UNKNOWN = "unknown"


class Decision(str, Enum):
    """The deterministic result returned by the policy enforcer."""

    ALLOW = "allow"
    HALT = "halt"
    ESCALATE = "escalate"


class AssetCriticality(str, Enum):
    """Business impact classification for the asset targeted by an action."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Environment(str, Enum):
    """Deployment boundary supplied by the trusted action transport."""

    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


class DbArgs(BaseModel):
    """Arguments for the intentionally constrained local SQLite capability."""

    sql: str = Field(min_length=1)


class TransferArgs(BaseModel):
    """Arguments for a mock money-transfer capability."""

    cents: int = Field(ge=0)
    to: str = Field(min_length=1)


class FsWriteArgs(BaseModel):
    """Arguments for a filesystem mutation inside the demo sandbox."""

    path: str = Field(min_length=1)
    content: str


class InspectArgs(BaseModel):
    """Arguments for a strict read-only sandbox inspection capability."""

    resource: Literal["sandbox_files", "ledger", "db_schema"]


class GitHubArgs(BaseModel):
    """Typed, provider-neutral subset of developer repository operations."""

    operation: Literal[
        "read_issue",
        "read_pull_request",
        "create_branch",
        "open_pull_request",
        "merge_pull_request",
    ]
    repository: str = Field(min_length=3)
    branch: str | None = None
    issue_number: int | None = Field(default=None, ge=1)
    pull_request_number: int | None = Field(default=None, ge=1)


class DbAction(BaseModel):
    tool: Literal["db"] = "db"
    args: DbArgs


class TransferAction(BaseModel):
    tool: Literal["transfer"] = "transfer"
    args: TransferArgs


class FsWriteAction(BaseModel):
    tool: Literal["fs_write"] = "fs_write"
    args: FsWriteArgs


class InspectAction(BaseModel):
    tool: Literal["inspect"] = "inspect"
    args: InspectArgs


class GitHubAction(BaseModel):
    tool: Literal["github"] = "github"
    args: GitHubArgs


ProposedAction: TypeAlias = DbAction | TransferAction | FsWriteAction | InspectAction | GitHubAction


class Policy(BaseModel):
    """Machine-checkable, human-confirmed intent for one agent run."""

    task: str
    allowed_tools: set[str] = Field(default_factory=set)
    allowed_roots: list[str] = Field(default_factory=list)
    allowed_db_ops: set[str] = Field(default_factory=set)
    allowed_db_tables: set[str] = Field(default_factory=set)
    spend_cap_cents: int = Field(default=0, ge=0)
    forbidden_patterns: list[str] = Field(default_factory=list)
    allowed_agent_ids: set[str] = Field(default_factory=set)
    allowed_human_principals: set[str] = Field(default_factory=set)
    allowed_environments: set[Environment] = Field(default_factory=set)
    allowed_asset_ids: set[str] = Field(default_factory=set)
    allowed_github_operations: set[str] = Field(default_factory=set)
    allowed_github_repositories: set[str] = Field(default_factory=set)
    max_asset_criticality: AssetCriticality = AssetCriticality.HIGH
    expires_at_epoch: int | None = Field(default=None, ge=0)


class EnforcementContext(BaseModel):
    """Immutable run-state snapshot supplied to a deterministic decision."""

    spent_cents: int = Field(default=0, ge=0)
    agent_id: str = Field(default="local-demo-agent", min_length=1)
    human_principal: str = Field(default="local-demo-user", min_length=1)
    environment: Environment = Environment.LOCAL
    asset_id: str = Field(default="local-sandbox", min_length=1)
    asset_criticality: AssetCriticality = AssetCriticality.LOW
    session_id: str = Field(default="local-demo-session", min_length=1)
    evaluated_at_epoch: int = Field(default=0, ge=0)


class Verdict(BaseModel):
    """An auditable enforcement outcome."""

    model_config = ConfigDict(frozen=False)

    decision: Decision
    reversibility: Reversibility
    reason: str
    matched_rule: str
    action: ProposedAction
