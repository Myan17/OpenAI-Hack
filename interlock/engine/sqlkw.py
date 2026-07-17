"""Conservative helpers for the limited SQL grammar accepted by Interlock."""

import re

_KEYWORD = re.compile(r"^[A-Za-z]+")
_TABLE_PATTERNS: dict[str, re.Pattern[str]] = {
    "DELETE": re.compile(r"^DELETE\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.IGNORECASE),
    "INSERT": re.compile(r"^INSERT\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.IGNORECASE),
    "SELECT": re.compile(r"\bFROM\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.IGNORECASE),
    "UPDATE": re.compile(r"^UPDATE\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.IGNORECASE),
}


def normalized_statement(sql: str) -> str | None:
    """Return one comment-free SQL statement, or ``None`` for ambiguous input."""

    statement = sql.strip()
    if not statement or "--" in statement or "/*" in statement:
        return None
    if ";" in statement:
        if not statement.endswith(";") or statement[:-1].count(";"):
            return None
        statement = statement[:-1].rstrip()
    return statement or None


def leading_keyword(sql: str) -> str | None:
    """Return the uppercase leading SQL keyword for one accepted statement."""

    statement = normalized_statement(sql)
    if statement is None:
        return None
    match = _KEYWORD.match(statement)
    return match.group(0).upper() if match else None


def target_table(sql: str) -> str | None:
    """Extract a simple, unquoted table target from one accepted SQL statement."""

    statement = normalized_statement(sql)
    keyword = leading_keyword(sql)
    if statement is None or keyword is None:
        return None
    pattern = _TABLE_PATTERNS.get(keyword)
    if pattern is None:
        return None
    match = pattern.search(statement)
    return match.group(1).lower() if match else None
