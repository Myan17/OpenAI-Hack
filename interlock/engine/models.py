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


ProposedAction: TypeAlias = DbAction | TransferAction | FsWriteAction | InspectAction


class Policy(BaseModel):
    """Machine-checkable, human-confirmed intent for one agent run."""

    task: str
    allowed_tools: set[str] = Field(default_factory=set)
    allowed_roots: list[str] = Field(default_factory=list)
    allowed_db_ops: set[str] = Field(default_factory=set)
    allowed_db_tables: set[str] = Field(default_factory=set)
    spend_cap_cents: int = Field(default=0, ge=0)
    forbidden_patterns: list[str] = Field(default_factory=list)


class EnforcementContext(BaseModel):
    """Immutable run-state snapshot supplied to a deterministic decision."""

    spent_cents: int = Field(default=0, ge=0)


class Verdict(BaseModel):
    """An auditable enforcement outcome."""

    model_config = ConfigDict(frozen=False)

    decision: Decision
    reversibility: Reversibility
    reason: str
    matched_rule: str
    action: ProposedAction
