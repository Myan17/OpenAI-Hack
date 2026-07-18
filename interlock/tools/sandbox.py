"""Real local effects contained to a SQLite file, one root, and an in-memory ledger."""

import sqlite3
from pathlib import Path


class Sandbox:
    """Per-run local sandbox; it never reaches real files, networks, or money."""

    def __init__(
        self, root: Path, opening_balance_cents: int = 100_000, reset: bool = True
    ) -> None:
        if opening_balance_cents < 0:
            raise ValueError("opening balance cannot be negative")
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._db_path = self.root / "sandbox.sqlite"
        self._initialize_database(opening_balance_cents, reset)

    def run_db(self, sql: str) -> dict[str, object]:
        """Run one SQL statement against this sandbox's SQLite file."""

        with sqlite3.connect(self._db_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(sql)
            rows = [dict(row) for row in cursor.fetchall()]
            return {"rows": rows, "rowcount": cursor.rowcount}

    def transfer(self, cents: int, to: str) -> dict[str, int | str]:
        """Apply a mock in-memory transfer with no external side effect."""

        if cents < 0:
            raise ValueError("transfer cents cannot be negative")
        if not to:
            raise ValueError("transfer recipient is required")
        with sqlite3.connect(self._db_path) as connection:
            balance = int(connection.execute("SELECT cents FROM ledger WHERE id = 1").fetchone()[0])
            if cents > balance:
                raise ValueError("insufficient sandbox balance")
            remaining = balance - cents
            connection.execute("UPDATE ledger SET cents = ? WHERE id = 1", (remaining,))
        return {"to": to, "cents": cents, "balance_cents": remaining}

    def fs_write(self, relative_path: str, content: str) -> dict[str, str]:
        """Write beneath the sandbox root and reject traversal or symlink escapes."""

        path = (self.root / relative_path).resolve()
        try:
            path.relative_to(self.root)
        except ValueError as error:
            raise ValueError("path is outside the sandbox root") from error
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"path": str(path.relative_to(self.root)), "content": content}

    def inspect(self, resource: str) -> dict[str, object]:
        """Return an explicitly limited read-only snapshot for an agent tool."""

        if resource == "ledger":
            with sqlite3.connect(self._db_path) as connection:
                balance = int(connection.execute("SELECT cents FROM ledger WHERE id = 1").fetchone()[0])
            return {"balance_cents": balance}
        if resource == "sandbox_files":
            return {"paths": sorted(str(path.relative_to(self.root)) for path in self.root.rglob("*") if path.is_file())}
        if resource == "db_schema":
            return self.run_db("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")
        raise ValueError("unknown inspection resource")

    def github(
        self,
        operation: str,
        repository: str,
        branch: str | None = None,
        issue_number: int | None = None,
        pull_request_number: int | None = None,
    ) -> dict[str, object]:
        """Return a contained GitHub-style adapter receipt without contacting GitHub."""

        result: dict[str, object] = {"operation": operation, "repository": repository}
        if branch is not None:
            result["branch"] = branch
        if issue_number is not None:
            result["issue_number"] = issue_number
        if pull_request_number is not None:
            result["pull_request_number"] = pull_request_number
        return result

    def _initialize_database(self, opening_balance_cents: int, reset: bool) -> None:
        """Create a deterministic demo fixture once for this sandbox root."""

        with sqlite3.connect(self._db_path) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, stale INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS ledger (id INTEGER PRIMARY KEY CHECK (id = 1), cents INTEGER NOT NULL);
                """
            )
            if reset:
                connection.executescript(
                    """
                    DELETE FROM users;
                    DELETE FROM sessions;
                    DELETE FROM ledger;
                    INSERT INTO users (id, email) VALUES (1, 'ada@example.test'), (2, 'grace@example.test');
                    INSERT INTO sessions (id, user_id, stale) VALUES (1, 1, 1), (2, 2, 0);
                    """
                )
                connection.execute("INSERT INTO ledger (id, cents) VALUES (1, ?)", (opening_balance_cents,))
            else:
                connection.execute(
                    "INSERT OR IGNORE INTO ledger (id, cents) VALUES (1, ?)",
                    (opening_balance_cents,),
                )
