"""SQLite persistence for non-authoritative, reviewer-governed assurance cases."""

import re
import sqlite3
from pathlib import Path

from interlock.assurance.models import AssuranceCase


_SECRET_LIKE_PATTERN = re.compile(r"(?:OPENAI_API_KEY\s*=|\bBearer\s+|\bsk-[A-Za-z0-9_-]{8,})", re.IGNORECASE)


class AssuranceStore:
    """Store candidates separately from runtime policy and enforcement decisions."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._initialize()

    def create_candidate(self, *, title: str, summary: str, source: str, owner: str) -> AssuranceCase:
        """Persist a redaction-safe candidate that has no authority until reviewed."""

        if _SECRET_LIKE_PATTERN.search(summary):
            raise ValueError("secret-like candidate payload must be redacted before storage")
        with sqlite3.connect(self._db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO assurance_cases (title, summary, source, owner, status)
                VALUES (?, ?, ?, ?, 'pending_review')
                """,
                (title, summary, source, owner),
            )
            case_id = int(cursor.lastrowid)
        return self.case(case_id)

    def review_candidate(self, case_id: int, resolution: str, *, reviewer: str) -> AssuranceCase | None:
        """Resolve a pending candidate exactly once; only approval makes it active."""

        if resolution not in {"approved", "rejected"}:
            raise ValueError("candidate resolution must be approved or rejected")
        if not reviewer:
            raise ValueError("reviewer is required")
        status = "active" if resolution == "approved" else "rejected"
        with sqlite3.connect(self._db_path) as connection:
            cursor = connection.execute(
                """
                UPDATE assurance_cases
                SET status = ?, reviewer = ?
                WHERE id = ? AND status = 'pending_review'
                """,
                (status, reviewer, case_id),
            )
            if cursor.rowcount != 1:
                return None
        return self.case(case_id)

    def case(self, case_id: int) -> AssuranceCase:
        """Return one stored case or fail explicitly when it does not exist."""

        with sqlite3.connect(self._db_path) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT id, title, summary, source, owner, status, reviewer FROM assurance_cases WHERE id = ?",
                (case_id,),
            ).fetchone()
        if row is None:
            raise ValueError("assurance case does not exist")
        return _case_from_row(row)

    def active_cases(self) -> list[AssuranceCase]:
        """Return only reviewer-approved cases eligible for a replay suite."""

        return self._cases("WHERE status = 'active'")

    def all_cases(self) -> list[AssuranceCase]:
        """Return all candidates for review screens without granting authority."""

        return self._cases("")

    def _cases(self, where: str) -> list[AssuranceCase]:
        with sqlite3.connect(self._db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT id, title, summary, source, owner, status, reviewer "
                f"FROM assurance_cases {where} ORDER BY id"
            ).fetchall()
        return [_case_from_row(row) for row in rows]

    def _initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS assurance_cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    source TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (
                        status IN ('pending_review', 'active', 'rejected', 'expired', 'retired', 'revoked')
                    ),
                    reviewer TEXT
                )
                """
            )


def _case_from_row(row: sqlite3.Row) -> AssuranceCase:
    """Map a SQLite row into the strict public assurance-case representation."""

    return AssuranceCase(
        case_id=int(row["id"]),
        title=str(row["title"]),
        summary=str(row["summary"]),
        source=str(row["source"]),
        owner=str(row["owner"]),
        status=str(row["status"]),
        reviewer=str(row["reviewer"]) if row["reviewer"] is not None else None,
    )
