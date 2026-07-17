"""Append-only SQLite audit log for Interlock verdicts."""

import json
import sqlite3
import asyncio
from datetime import UTC, datetime
from pathlib import Path

from pydantic import TypeAdapter

from interlock.engine.models import Policy, ProposedAction, Verdict
from interlock.tracing import trace_verdict

_ACTION_ADAPTER = TypeAdapter(ProposedAction)


class EventLog:
    """SQLite-backed event sink that returns a stable append identifier."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._subscribers: list[asyncio.Queue[dict[str, object]]] = []
        self._initialize()

    def emit(self, verdict: Verdict) -> int:
        """Append a verdict and return its event id."""

        with sqlite3.connect(self._db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO events (ts, tool, decision, reversibility, reason, matched_rule, args_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(UTC).isoformat(),
                    verdict.action.tool,
                    verdict.decision.value,
                    verdict.reversibility.value,
                    verdict.reason,
                    verdict.matched_rule,
                    json.dumps(verdict.action.model_dump(mode="json"), sort_keys=True),
                ),
            )
            event_id = int(cursor.lastrowid)
        event = self.since(event_id - 1)[0]
        for subscriber in self._subscribers:
            subscriber.put_nowait(event)
        _schedule_verdict_trace(verdict)
        return event_id

    @property
    def db_path(self) -> Path:
        """Return the SQLite location so app wiring can place its local sandbox beside it."""

        return self._db_path

    def subscribe(self) -> asyncio.Queue[dict[str, object]]:
        """Return a queue that receives each newly appended event."""
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, object]]) -> None:
        """Remove a disconnected SSE consumer without affecting other subscribers."""

        try:
            self._subscribers.remove(queue)
        except ValueError:
            pass

    def record_escalation(self, event_id: int, action: ProposedAction, policy: Policy) -> None:
        """Persist an unexecuted escalation so approval survives a process restart."""

        with sqlite3.connect(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO escalations (event_id, action_json, policy_json, status)
                VALUES (?, ?, ?, 'pending')
                """,
                (
                    event_id,
                    action.model_dump_json(),
                    policy.model_dump_json(),
                ),
            )

    def claim_escalation(
        self, event_id: int, resolution: str
    ) -> tuple[ProposedAction, Policy] | None:
        """Atomically claim one pending escalation for approval or rejection."""

        if resolution not in {"approved", "rejected"}:
            raise ValueError("resolution must be approved or rejected")
        with sqlite3.connect(self._db_path) as connection:
            cursor = connection.execute(
                "UPDATE escalations SET status = ? WHERE event_id = ? AND status = 'pending'",
                (resolution, event_id),
            )
            if cursor.rowcount != 1:
                return None
            row = connection.execute(
                "SELECT action_json, policy_json FROM escalations WHERE event_id = ?", (event_id,)
            ).fetchone()
        if row is None:
            return None
        return _ACTION_ADAPTER.validate_json(row[0]), Policy.model_validate_json(row[1])

    def start_run(self) -> int:
        """Persist a run start before the background agent is invoked."""

        with sqlite3.connect(self._db_path) as connection:
            cursor = connection.execute(
                "INSERT INTO runs (status, detail) VALUES ('running', 'Agent run started.')"
            )
            return int(cursor.lastrowid)

    def finish_run(self, run_id: int, status: str, detail: str) -> None:
        """Persist a terminal result for a previously started agent run."""

        if status not in {"completed", "failed"}:
            raise ValueError("run status must be completed or failed")
        with sqlite3.connect(self._db_path) as connection:
            connection.execute(
                "UPDATE runs SET status = ?, detail = ? WHERE id = ?", (status, detail, run_id)
            )

    def runs(self) -> list[dict[str, object]]:
        """Return durable agent-run states for the dashboard or polling clients."""

        with sqlite3.connect(self._db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute("SELECT id, status, detail FROM runs ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]

    def since(self, event_id: int) -> list[dict[str, object]]:
        """Return audit rows strictly newer than an event id."""

        with sqlite3.connect(self._db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT id, ts, tool, decision, reversibility, reason, matched_rule, args_json "
                "FROM events WHERE id > ? ORDER BY id",
                (event_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def _initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    tool TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reversibility TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    matched_rule TEXT NOT NULL,
                    args_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
                    detail TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS escalations (
                    event_id INTEGER PRIMARY KEY REFERENCES events(id),
                    action_json TEXT NOT NULL,
                    policy_json TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected'))
                )
                """
            )


def _schedule_verdict_trace(verdict: Verdict) -> None:
    """Schedule optional observability after persistence without blocking tool enforcement."""

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(asyncio.to_thread(trace_verdict, verdict))
