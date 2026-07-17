"""Run deterministic golden scenarios against a fixed least-privilege policy."""

from pathlib import Path

import yaml
from pydantic import TypeAdapter

from interlock.engine.enforcer import enforce
from interlock.engine.models import EnforcementContext, Policy, ProposedAction


def run_eval(path: Path | None = None) -> dict[str, int | bool]:
    source = path or Path(__file__).with_name("scenarios.yaml")
    scenarios = yaml.safe_load(source.read_text())["scenarios"]
    adapter = TypeAdapter(ProposedAction)
    policy = Policy(task="clean sessions", allowed_tools={"db", "inspect", "transfer"}, allowed_db_ops={"SELECT", "DELETE"}, allowed_db_tables={"sessions"}, spend_cap_cents=500, forbidden_patterns=[r"DROP\s+TABLE"])
    totals = {"halted_bad": 0, "missed_bad": 0, "blocked_good": 0, "allowed_good": 0}
    for scenario in scenarios:
        verdict = enforce(adapter.validate_python(scenario["action"]), policy, EnforcementContext.model_validate(scenario.get("context", {})))
        good = scenario["expect"] == "allow"
        if good and verdict.decision.value == "allow": totals["allowed_good"] += 1
        elif good: totals["blocked_good"] += 1
        elif verdict.decision.value == "halt": totals["halted_bad"] += 1
        else: totals["missed_bad"] += 1
    return {**totals, "pass": totals["missed_bad"] == 0 and totals["blocked_good"] == 0}


if __name__ == "__main__":
    print(run_eval())
