from pathlib import Path

from interlock.engine.scope import (
    db_op_allowed,
    db_table_allowed,
    path_in_scope,
    within_spend,
)


def test_path_scope_uses_canonical_containment(tmp_path: Path) -> None:
    root = tmp_path / "demo"
    root.mkdir()

    assert path_in_scope(root / "notes.txt", [str(root)])
    assert not path_in_scope(root / ".." / "outside.txt", [str(root)])


def test_path_scope_rejects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "demo"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = root / "escape"
    link.symlink_to(outside, target_is_directory=True)

    assert not path_in_scope(link / "secret.txt", [str(root)])


def test_db_scope_checks_operation_and_table() -> None:
    sql = "DELETE FROM sessions WHERE id = 1"

    assert db_op_allowed(sql, {"DELETE"})
    assert db_table_allowed(sql, {"sessions"})
    assert not db_table_allowed(sql, {"users"})
    assert not db_op_allowed("SELECT 1; DROP TABLE users", {"SELECT"})


def test_spend_cap_is_cumulative() -> None:
    assert within_spend(spent_cents=300, requested_cents=200, cap_cents=500)
    assert not within_spend(spent_cents=301, requested_cents=200, cap_cents=500)
