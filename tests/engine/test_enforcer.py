from interlock.engine.enforcer import enforce
from interlock.engine.models import (
    AssetCriticality,
    DbAction,
    DbArgs,
    Decision,
    EnforcementContext,
    FsWriteAction,
    FsWriteArgs,
    GitHubAction,
    GitHubArgs,
    InspectAction,
    InspectArgs,
    Policy,
    TransferAction,
    TransferArgs,
)


def policy(**overrides: object) -> Policy:
    base = {
        "task": "clean sessions",
        "allowed_tools": {"db", "fs_write", "transfer", "inspect"},
        "allowed_roots": ["/tmp/demo"],
        "allowed_db_ops": {"SELECT", "DELETE"},
        "allowed_db_tables": {"sessions"},
        "spend_cap_cents": 500,
        "forbidden_patterns": [r"DROP\s+TABLE"],
    }
    base.update(overrides)
    return Policy(**base)


def test_disallowed_tool_halts() -> None:
    verdict = enforce(
        TransferAction(args=TransferArgs(cents=10, to="vendor")),
        policy(allowed_tools={"db"}),
        EnforcementContext(),
    )
    assert verdict.decision == Decision.HALT
    assert verdict.matched_rule == "allowed_tools"


def test_forbidden_pattern_halts_before_scope() -> None:
    verdict = enforce(
        DbAction(args=DbArgs(sql="DROP TABLE users")), policy(), EnforcementContext()
    )
    assert verdict.decision == Decision.HALT
    assert verdict.matched_rule.startswith("forbidden_pattern:")


def test_recognized_read_allows() -> None:
    verdict = enforce(
        InspectAction(args=InspectArgs(resource="ledger")), policy(), EnforcementContext()
    )
    assert verdict.decision == Decision.ALLOW
    assert verdict.matched_rule == "reversible"


def test_read_from_unapproved_database_table_halts() -> None:
    verdict = enforce(
        DbAction(args=DbArgs(sql="SELECT * FROM users")), policy(), EnforcementContext()
    )

    assert verdict.decision == Decision.HALT
    assert verdict.matched_rule == "allowed_db_tables"


def test_database_table_outside_scope_halts() -> None:
    verdict = enforce(
        DbAction(args=DbArgs(sql="DELETE FROM users")), policy(), EnforcementContext()
    )
    assert verdict.decision == Decision.HALT
    assert verdict.matched_rule == "allowed_db_tables"


def test_in_scope_mutation_escalates() -> None:
    verdict = enforce(
        DbAction(args=DbArgs(sql="DELETE FROM sessions WHERE id = 1")),
        policy(),
        EnforcementContext(),
    )
    assert verdict.decision == Decision.ESCALATE
    assert verdict.matched_rule == "irreversible_in_scope"


def test_over_cap_transfer_halts() -> None:
    verdict = enforce(
        TransferAction(args=TransferArgs(cents=201, to="vendor")),
        policy(),
        EnforcementContext(spent_cents=300),
    )
    assert verdict.decision == Decision.HALT
    assert verdict.matched_rule == "spend_cap"


def test_out_of_root_file_write_halts() -> None:
    verdict = enforce(
        FsWriteAction(args=FsWriteArgs(path="/etc/passwd", content="x")),
        policy(),
        EnforcementContext(),
    )
    assert verdict.decision == Decision.HALT
    assert verdict.matched_rule == "allowed_roots"


def test_identity_scoped_policy_halts_an_unrecognized_agent() -> None:
    verdict = enforce(
        InspectAction(args=InspectArgs(resource="ledger")),
        policy(allowed_agent_ids={"release-agent"}),
        EnforcementContext(agent_id="untrusted-agent"),
    )

    assert verdict.decision == Decision.HALT
    assert verdict.matched_rule == "allowed_agent_ids"


def test_environment_and_asset_scope_are_enforced_before_tool_execution() -> None:
    verdict = enforce(
        InspectAction(args=InspectArgs(resource="ledger")),
        policy(
            allowed_environments={"staging"},
            allowed_asset_ids={"orders-db"},
            max_asset_criticality=AssetCriticality.MEDIUM,
        ),
        EnforcementContext(
            environment="production",
            asset_id="customer-db",
            asset_criticality=AssetCriticality.HIGH,
        ),
    )

    assert verdict.decision == Decision.HALT
    assert verdict.matched_rule == "allowed_environments"


def test_policy_expiry_halts_deterministically_from_supplied_context_time() -> None:
    verdict = enforce(
        InspectAction(args=InspectArgs(resource="ledger")),
        policy(expires_at_epoch=100),
        EnforcementContext(evaluated_at_epoch=101),
    )

    assert verdict.decision == Decision.HALT
    assert verdict.matched_rule == "expires_at_epoch"


def test_asset_criticality_ceiling_halts_even_an_authorized_read() -> None:
    verdict = enforce(
        InspectAction(args=InspectArgs(resource="ledger")),
        policy(max_asset_criticality=AssetCriticality.LOW),
        EnforcementContext(asset_criticality=AssetCriticality.HIGH),
    )

    assert verdict.decision == Decision.HALT
    assert verdict.matched_rule == "max_asset_criticality"


def test_scoped_github_read_is_allowed() -> None:
    verdict = enforce(
        GitHubAction(args=GitHubArgs(operation="read_issue", repository="acme/api")),
        policy(
            allowed_tools={"github"},
            allowed_github_operations={"read_issue"},
            allowed_github_repositories={"acme/api"},
        ),
        EnforcementContext(),
    )

    assert verdict.decision == Decision.ALLOW
    assert verdict.matched_rule == "reversible"


def test_github_mutation_in_scope_escalates() -> None:
    verdict = enforce(
        GitHubAction(
            args=GitHubArgs(operation="create_branch", repository="acme/api", branch="fix-incident")
        ),
        policy(
            allowed_tools={"github"},
            allowed_github_operations={"create_branch"},
            allowed_github_repositories={"acme/api"},
        ),
        EnforcementContext(),
    )

    assert verdict.decision == Decision.ESCALATE
    assert verdict.matched_rule == "irreversible_in_scope"


def test_github_repository_outside_scope_halts() -> None:
    verdict = enforce(
        GitHubAction(args=GitHubArgs(operation="read_issue", repository="other/private")),
        policy(
            allowed_tools={"github"},
            allowed_github_operations={"read_issue"},
            allowed_github_repositories={"acme/api"},
        ),
        EnforcementContext(),
    )

    assert verdict.decision == Decision.HALT
    assert verdict.matched_rule == "allowed_github_repositories"
