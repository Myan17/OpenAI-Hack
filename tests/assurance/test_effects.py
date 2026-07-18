"""Tests for deterministic effect-contract evaluation on sandbox state."""

from pathlib import Path

from interlock.assurance.effects import evaluate_effect_contract, sandbox_snapshot
from interlock.assurance.models import EffectContract
from interlock.tools.sandbox import Sandbox


def test_effect_contract_catches_unexpected_sandbox_mutation(tmp_path: Path) -> None:
    sandbox = Sandbox(tmp_path / "demo")
    contract = EffectContract(
        contract_id="no-session-delete",
        expected_session_count=2,
        expected_ledger_balance_cents=100_000,
    )

    passed = evaluate_effect_contract(contract, sandbox_snapshot(sandbox))
    sandbox.run_db("DELETE FROM sessions WHERE id = 1")
    failed = evaluate_effect_contract(contract, sandbox_snapshot(sandbox))

    assert passed.passed is True
    assert failed.passed is False
    assert failed.violations == ("expected_session_count: expected 2, observed 1",)
