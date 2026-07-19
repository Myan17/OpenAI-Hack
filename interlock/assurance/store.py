"""SQLite persistence for non-authoritative, reviewer-governed assurance cases."""

import re
import sqlite3
from pathlib import Path

from pydantic import TypeAdapter

from interlock.assurance.models import AssuranceCase, ReplayCaseResult
from interlock.assurance.replay import replay_case
from interlock.engine.models import Policy
from interlock.engine.simulator import SimulationStep


_SENSITIVE_PATTERN = re.compile(
    r"(?:OPENAI_API_KEY\s*=|\bBearer\s+|\bsk-[A-Za-z0-9_-]{8,}|\b[^\s@]+@[^\s@]+\.[^\s@]+\b)",
    re.IGNORECASE,
)
_STEPS_ADAPTER = TypeAdapter(list[SimulationStep])


class AssuranceStore:
    """Store candidates separately from runtime policy and enforcement decisions."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._initialize()

    def create_candidate(
        self,
        *,
        title: str,
        summary: str,
        source: str,
        owner: str,
        expires_at_epoch: int | None = None,
    ) -> AssuranceCase:
        """Persist a redaction-safe candidate that has no authority until reviewed."""

        if _SENSITIVE_PATTERN.search(summary):
            raise ValueError("sensitive secret-like candidate payload must be redacted before storage")
        with sqlite3.connect(self._db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO assurance_cases (title, summary, source, owner, status, expires_at_epoch)
                VALUES (?, ?, ?, ?, 'pending_review', ?)
                """,
                (title, summary, source, owner, expires_at_epoch),
            )
            case_id = int(cursor.lastrowid)
            self._audit(connection, case_id, "created", owner)
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
            self._audit(connection, case_id, resolution, reviewer)
        return self.case(case_id)

    def case(self, case_id: int) -> AssuranceCase:
        """Return one stored case or fail explicitly when it does not exist."""

        with sqlite3.connect(self._db_path) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT id, title, summary, source, owner, status, reviewer, expires_at_epoch "
                "FROM assurance_cases WHERE id = ?",
                (case_id,),
            ).fetchone()
        if row is None:
            raise ValueError("assurance case does not exist")
        return _case_from_row(row)

    def active_cases(self, now_epoch: int | None = None) -> list[AssuranceCase]:
        """Return only reviewer-approved cases eligible for a replay suite."""

        if now_epoch is not None:
            self.expire_cases(now_epoch)
        return self._cases("WHERE status = 'active'")

    def all_cases(self) -> list[AssuranceCase]:
        """Return all candidates for review screens without granting authority."""

        return self._cases("")

    def expire_cases(self, now_epoch: int) -> int:
        """Expire active cases using caller-supplied time, keeping replay deterministic."""

        with sqlite3.connect(self._db_path) as connection:
            rows = connection.execute(
                """
                SELECT id FROM assurance_cases
                WHERE status = 'active' AND expires_at_epoch IS NOT NULL AND expires_at_epoch < ?
                """,
                (now_epoch,),
            ).fetchall()
            for row in rows:
                case_id = int(row[0])
                connection.execute("UPDATE assurance_cases SET status = 'expired' WHERE id = ?", (case_id,))
                self._audit(connection, case_id, "expired", "system")
        return len(rows)

    def retire_case(self, case_id: int, *, actor: str) -> AssuranceCase | None:
        """Retire one active case explicitly; retired cases cannot be re-approved."""

        if not actor:
            raise ValueError("retirement actor is required")
        with sqlite3.connect(self._db_path) as connection:
            cursor = connection.execute(
                "UPDATE assurance_cases SET status = 'retired' WHERE id = ? AND status = 'active'",
                (case_id,),
            )
            if cursor.rowcount != 1:
                return None
            self._audit(connection, case_id, "retired", actor)
        return self.case(case_id)

    def audit_events(self, case_id: int) -> list[dict[str, object]]:
        """Return append-only lifecycle evidence for one assurance case."""

        with sqlite3.connect(self._db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT id, case_id, action, actor FROM assurance_case_audit WHERE case_id = ? ORDER BY id",
                (case_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def export_snapshot(self) -> dict[str, object]:
        """Return a deterministic local recovery snapshot without runtime-policy data."""

        with sqlite3.connect(self._db_path) as connection:
            connection.row_factory = sqlite3.Row
            fixture_rows = connection.execute(
                "SELECT case_id, policy_json, steps_json FROM assurance_replay_fixtures ORDER BY case_id"
            ).fetchall()
            audit_rows = connection.execute(
                "SELECT id, case_id, action, actor FROM assurance_case_audit ORDER BY id"
            ).fetchall()
        return {
            "schema_version": 1,
            "cases": [case.model_dump(mode="json") for case in self.all_cases()],
            "fixtures": [dict(row) for row in fixture_rows],
            "audit_events": [dict(row) for row in audit_rows],
        }

    def import_snapshot(self, snapshot: dict[str, object]) -> int:
        """Restore a validated snapshot only into an empty store; never overwrite evidence."""

        if snapshot.get("schema_version") != 1:
            raise ValueError("unsupported assurance snapshot schema")
        cases_value = snapshot.get("cases")
        fixtures_value = snapshot.get("fixtures")
        audits_value = snapshot.get("audit_events")
        if not isinstance(cases_value, list) or not isinstance(fixtures_value, list) or not isinstance(audits_value, list):
            raise ValueError("assurance snapshot must contain case, fixture, and audit lists")
        try:
            cases = TypeAdapter(list[AssuranceCase]).validate_python(cases_value)
        except ValueError as error:
            raise ValueError("assurance snapshot cases are invalid") from error
        case_ids = {case.case_id for case in cases}
        if len(case_ids) != len(cases) or any(_SENSITIVE_PATTERN.search(case.summary) for case in cases):
            raise ValueError("assurance snapshot cases are invalid")
        fixtures = [_validated_fixture(item, case_ids) for item in fixtures_value]
        audits = [_validated_audit(item, case_ids) for item in audits_value]

        with sqlite3.connect(self._db_path) as connection:
            existing = int(connection.execute("SELECT COUNT(*) FROM assurance_cases").fetchone()[0])
            if existing:
                raise ValueError("assurance snapshot import requires an empty store")
            for case in cases:
                connection.execute(
                    """
                    INSERT INTO assurance_cases
                    (id, title, summary, source, owner, status, reviewer, expires_at_epoch)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        case.case_id, case.title, case.summary, case.source, case.owner,
                        case.status, case.reviewer, case.expires_at_epoch,
                    ),
                )
            for case_id, policy_json, steps_json in fixtures:
                connection.execute(
                    "INSERT INTO assurance_replay_fixtures (case_id, policy_json, steps_json) VALUES (?, ?, ?)",
                    (case_id, policy_json, steps_json),
                )
            for event_id, case_id, action, actor in audits:
                connection.execute(
                    "INSERT INTO assurance_case_audit (id, case_id, action, actor) VALUES (?, ?, ?, ?)",
                    (event_id, case_id, action, actor),
                )
        return len(cases)

    def attach_replay_fixture(
        self, case_id: int, *, policy: Policy, steps: list[SimulationStep]
    ) -> None:
        """Bind one approved case to an immutable, effect-free replay fixture."""

        case = self.case(case_id)
        if case.status != "active":
            raise ValueError("only an active reviewer-approved case can receive a replay fixture")
        with sqlite3.connect(self._db_path) as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO assurance_replay_fixtures (case_id, policy_json, steps_json)
                    VALUES (?, ?, ?)
                    """,
                    (
                        case_id,
                        policy.model_dump_json(),
                        _STEPS_ADAPTER.dump_json(steps).decode("utf-8"),
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise ValueError("case already has a replay fixture; retire and replace explicitly") from error

    def replay_active_case(self, case_id: int) -> ReplayCaseResult:
        """Run an approved fixture through the existing side-effect-free simulator."""

        case = self.case(case_id)
        if case.status != "active":
            raise ValueError("only an active reviewer-approved case can be replayed")
        with sqlite3.connect(self._db_path) as connection:
            row = connection.execute(
                "SELECT policy_json, steps_json FROM assurance_replay_fixtures WHERE case_id = ?",
                (case_id,),
            ).fetchone()
        if row is None:
            raise ValueError("active case has no replay fixture")
        return replay_case(
            case_id=case_id,
            policy=Policy.model_validate_json(row[0]),
            steps=_STEPS_ADAPTER.validate_json(row[1]),
        )

    def _cases(self, where: str) -> list[AssuranceCase]:
        with sqlite3.connect(self._db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT id, title, summary, source, owner, status, reviewer, expires_at_epoch "
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
                    reviewer TEXT,
                    expires_at_epoch INTEGER
                )
                """
            )
            columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(assurance_cases)")}
            if "expires_at_epoch" not in columns:
                connection.execute("ALTER TABLE assurance_cases ADD COLUMN expires_at_epoch INTEGER")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS assurance_replay_fixtures (
                    case_id INTEGER PRIMARY KEY REFERENCES assurance_cases(id),
                    policy_json TEXT NOT NULL,
                    steps_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS assurance_case_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id INTEGER NOT NULL REFERENCES assurance_cases(id),
                    action TEXT NOT NULL,
                    actor TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _audit(connection: sqlite3.Connection, case_id: int, action: str, actor: str) -> None:
        """Append immutable lifecycle evidence inside the caller's SQLite transaction."""

        connection.execute(
            "INSERT INTO assurance_case_audit (case_id, action, actor) VALUES (?, ?, ?)",
            (case_id, action, actor),
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
        expires_at_epoch=int(row["expires_at_epoch"]) if row["expires_at_epoch"] is not None else None,
    )


def _validated_fixture(item: object, case_ids: set[int]) -> tuple[int, str, str]:
    """Validate a portable fixture before any recovery write is attempted."""

    if not isinstance(item, dict):
        raise ValueError("assurance snapshot fixture is invalid")
    case_id = item.get("case_id")
    policy_json = item.get("policy_json")
    steps_json = item.get("steps_json")
    if not isinstance(case_id, int) or case_id not in case_ids or not isinstance(policy_json, str) or not isinstance(steps_json, str):
        raise ValueError("assurance snapshot fixture is invalid")
    try:
        Policy.model_validate_json(policy_json)
        _STEPS_ADAPTER.validate_json(steps_json)
    except ValueError as error:
        raise ValueError("assurance snapshot fixture is invalid") from error
    return case_id, policy_json, steps_json


def _validated_audit(item: object, case_ids: set[int]) -> tuple[int, int, str, str]:
    """Validate immutable lifecycle evidence and its case reference before recovery."""

    if not isinstance(item, dict):
        raise ValueError("assurance snapshot audit event is invalid")
    event_id = item.get("id")
    case_id = item.get("case_id")
    action = item.get("action")
    actor = item.get("actor")
    if not isinstance(event_id, int) or event_id < 1 or not isinstance(case_id, int) or case_id not in case_ids:
        raise ValueError("assurance snapshot audit event is invalid")
    if not isinstance(action, str) or not action or not isinstance(actor, str) or not actor:
        raise ValueError("assurance snapshot audit event is invalid")
    return event_id, case_id, action, actor
