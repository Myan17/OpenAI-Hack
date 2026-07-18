"""Conservative reversibility classifiers for Interlock's typed tool actions."""

from interlock.engine.models import (
    DbAction,
    FsWriteAction,
    GitHubAction,
    InspectAction,
    ProposedAction,
    Reversibility,
    TransferAction,
)
from interlock.engine.sqlkw import leading_keyword

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
def classify(action: ProposedAction) -> Reversibility:
    """Classify a typed action without assuming unknown input is safe."""

    if isinstance(action, InspectAction):
        return Reversibility.REVERSIBLE
    if isinstance(action, (TransferAction, FsWriteAction)):
        return Reversibility.IRREVERSIBLE
    if isinstance(action, GitHubAction):
        if action.args.operation in {"read_issue", "read_pull_request"}:
            return Reversibility.REVERSIBLE
        return Reversibility.IRREVERSIBLE
    if isinstance(action, DbAction):
        return _classify_sql(action.args.sql)
    return Reversibility.UNKNOWN


def _classify_sql(sql: str) -> Reversibility:
    """Classify one simple SQL statement; ambiguous syntax remains unknown."""

    keyword = leading_keyword(sql)
    if keyword is None:
        return Reversibility.UNKNOWN
    if keyword in _READ_ONLY_SQL:
        return Reversibility.REVERSIBLE
    if keyword in _MUTATING_SQL:
        return Reversibility.IRREVERSIBLE
    return Reversibility.UNKNOWN
