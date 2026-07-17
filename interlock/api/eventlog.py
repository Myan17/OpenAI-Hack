"""Append-only SQLite audit log for Interlock verdicts."""

import json
import sqlite3
import asyncio
from datetime import UTC, datetime
from pathlib import Path

from interlock.engine.models import Verdict


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
        return event_id

    def subscribe(self) -> asyncio.Queue[dict[str, object]]:
        """Return a queue that receives each newly appended event."""
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

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
