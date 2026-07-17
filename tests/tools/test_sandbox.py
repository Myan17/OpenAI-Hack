from pathlib import Path

import pytest

from interlock.tools.sandbox import Sandbox


def test_sandbox_runs_real_sqlite_queries_and_mutations(tmp_path: Path) -> None:
    sandbox = Sandbox(tmp_path / "demo")

    before = sandbox.run_db("SELECT count(*) AS count FROM sessions")
    sandbox.run_db("DELETE FROM sessions WHERE id = 1")
    after = sandbox.run_db("SELECT count(*) AS count FROM sessions")

    assert before["rows"][0]["count"] == 2
    assert after["rows"][0]["count"] == 1


def test_sandbox_transfer_mutates_only_its_in_memory_ledger(tmp_path: Path) -> None:
    sandbox = Sandbox(tmp_path / "demo", opening_balance_cents=1_000)

    receipt = sandbox.transfer(250, "vendor")

    assert receipt == {"to": "vendor", "cents": 250, "balance_cents": 750}


def test_sandbox_can_resume_existing_state_without_resetting_it(tmp_path: Path) -> None:
    root = tmp_path / "demo"
    first = Sandbox(root, opening_balance_cents=1_000)
    first.run_db("DELETE FROM sessions WHERE id = 1")
    first.transfer(250, "vendor")

    resumed = Sandbox(root, reset=False)

    assert resumed.run_db("SELECT count(*) AS count FROM sessions")["rows"][0]["count"] == 1
    assert resumed.inspect("ledger")["balance_cents"] == 750


def test_sandbox_file_write_stays_under_its_root(tmp_path: Path) -> None:
    sandbox = Sandbox(tmp_path / "demo")

    result = sandbox.fs_write("notes/todo.txt", "clean sessions")

    assert result["path"] == "notes/todo.txt"
    assert (tmp_path / "demo" / "notes" / "todo.txt").read_text() == "clean sessions"
    with pytest.raises(ValueError, match="sandbox root"):
        sandbox.fs_write("../outside.txt", "nope")
