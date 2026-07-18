"""Deterministic effect evidence over the local, contained demo sandbox."""

from interlock.assurance.models import EffectContract, EffectEvaluation, SandboxSnapshot
from interlock.tools.sandbox import Sandbox


def sandbox_snapshot(sandbox: Sandbox) -> SandboxSnapshot:
    """Capture the small state surface that the safe demo exposes for replay."""

    ledger = sandbox.inspect("ledger")
    sessions = sandbox.run_db("SELECT count(*) AS count FROM sessions")
    files = sandbox.inspect("sandbox_files")
    return SandboxSnapshot(
        ledger_balance_cents=int(ledger["balance_cents"]),
        session_count=int(sessions["rows"][0]["count"]),
        file_paths=tuple(str(path) for path in files["paths"] if path != "sandbox.sqlite"),
    )


def evaluate_effect_contract(contract: EffectContract, observed: SandboxSnapshot) -> EffectEvaluation:
    """Evaluate only explicit, reproducible sandbox-state assertions."""

    violations: list[str] = []
    if (
        contract.expected_ledger_balance_cents is not None
        and observed.ledger_balance_cents != contract.expected_ledger_balance_cents
    ):
        violations.append(
            "expected_ledger_balance_cents: expected "
            f"{contract.expected_ledger_balance_cents}, observed {observed.ledger_balance_cents}"
        )
    if contract.expected_session_count is not None and observed.session_count != contract.expected_session_count:
        violations.append(
            f"expected_session_count: expected {contract.expected_session_count}, observed {observed.session_count}"
        )
    forbidden = sorted(set(contract.forbidden_file_paths) & set(observed.file_paths))
    violations.extend(f"forbidden_file_path: {path}" for path in forbidden)
    return EffectEvaluation(
        contract_id=contract.contract_id,
        passed=not violations,
        violations=tuple(violations),
        observed=observed,
    )
