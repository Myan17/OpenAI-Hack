"""Conservative reversibility classifiers for Interlock's typed tool actions."""

import re

from interlock.engine.models import (
    DbAction,
    FsWriteAction,
    InspectAction,
    ProposedAction,
    Reversibility,
    TransferAction,
)

_READ_ONLY_SQL = frozenset({"SELECT", "EXPLAIN"})
_MUTATING_SQL = frozenset(
    {
        "ALTER",
        "ANALYZE",
        "ATTACH",
        "CREATE",
        "DELETE",
        "DETACH",
        "DROP",
        "INSERT",
        "PRAGMA",
        "REINDEX",
        "REPLACE",
        "UPDATE",
        "VACUUM",
    }
)
_SQL_KEYWORD = re.compile(r"^[A-Za-z]+")


def classify(action: ProposedAction) -> Reversibility:
    """Classify a typed action without assuming unknown input is safe."""

    if isinstance(action, InspectAction):
        return Reversibility.REVERSIBLE
    if isinstance(action, (TransferAction, FsWriteAction)):
        return Reversibility.IRREVERSIBLE
    if isinstance(action, DbAction):
        return _classify_sql(action.args.sql)
    return Reversibility.UNKNOWN


def _classify_sql(sql: str) -> Reversibility:
    """Classify one simple SQL statement; ambiguous syntax remains unknown."""

    statement = sql.strip()
    if not statement or "--" in statement or "/*" in statement:
        return Reversibility.UNKNOWN

    if ";" in statement:
        if not statement.endswith(";") or statement[:-1].count(";"):
            return Reversibility.UNKNOWN
        statement = statement[:-1].rstrip()

    match = _SQL_KEYWORD.match(statement)
    if match is None:
        return Reversibility.UNKNOWN

    keyword = match.group(0).upper()
    if keyword in _READ_ONLY_SQL:
        return Reversibility.REVERSIBLE
    if keyword in _MUTATING_SQL:
        return Reversibility.IRREVERSIBLE
    return Reversibility.UNKNOWN
