"""Deterministic scope checks for paths, database actions, and spend."""

from pathlib import Path

from interlock.engine.models import AssetCriticality
from interlock.engine.sqlkw import leading_keyword, target_table

_CRITICALITY_RANK = {
    AssetCriticality.LOW: 0,
    AssetCriticality.MEDIUM: 1,
    AssetCriticality.HIGH: 2,
}


def path_in_scope(path: str | Path, allowed_roots: list[str]) -> bool:
    """Return whether a path resolves beneath an approved sandbox root."""

    candidate = Path(path).resolve(strict=False)
    for root in allowed_roots:
        try:
            candidate.relative_to(Path(root).resolve(strict=False))
        except ValueError:
            continue
        return True
    return False


def db_op_allowed(sql: str, allowed_ops: set[str]) -> bool:
    """Return whether one validated SQL statement uses an approved operation."""

    keyword = leading_keyword(sql)
    return keyword is not None and keyword in allowed_ops


def db_table_allowed(sql: str, allowed_tables: set[str]) -> bool:
    """Return whether one validated SQL statement targets an approved table."""

    table = target_table(sql)
    return table is not None and table in {name.lower() for name in allowed_tables}


def within_spend(spent_cents: int, requested_cents: int, cap_cents: int) -> bool:
    """Return whether a requested transfer stays within a cumulative cap."""

    return requested_cents >= 0 and spent_cents >= 0 and spent_cents + requested_cents <= cap_cents


def value_in_scope(value: str, allowed_values: set[str]) -> bool:
    """Treat an empty configured set as an intentionally unscoped legacy policy."""

    return not allowed_values or value in allowed_values


def criticality_in_scope(actual: AssetCriticality, maximum: AssetCriticality) -> bool:
    """Return whether an asset is no more critical than its policy ceiling."""

    return _CRITICALITY_RANK[actual] <= _CRITICALITY_RANK[maximum]
