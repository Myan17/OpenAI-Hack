"""The pure, deterministic Interlock policy decision function."""

import re

from interlock.engine.catalog import classify
from interlock.engine.models import (
    DbAction,
    Decision,
    EnforcementContext,
    FsWriteAction,
    GitHubAction,
    Policy,
    ProposedAction,
    Reversibility,
    TransferAction,
    Verdict,
)
from interlock.engine.patterns import matches_forbidden
from interlock.engine.scope import (
    criticality_in_scope,
    db_op_allowed,
    db_table_allowed,
    path_in_scope,
    value_in_scope,
    within_spend,
)


def enforce(
    action: ProposedAction,
    policy: Policy,
    context: EnforcementContext,
) -> Verdict:
    """Return the deterministic verdict for one typed proposed action."""

    if policy.expires_at_epoch is not None and context.evaluated_at_epoch > policy.expires_at_epoch:
        return _verdict(
            Decision.HALT,
            Reversibility.UNKNOWN,
            "The confirmed policy has expired for this action context.",
            "expires_at_epoch",
            action,
        )

    if not value_in_scope(context.agent_id, policy.allowed_agent_ids):
        return _verdict(
            Decision.HALT,
            Reversibility.UNKNOWN,
            "This agent identity is not authorized by the confirmed policy.",
            "allowed_agent_ids",
            action,
        )

    if not value_in_scope(context.human_principal, policy.allowed_human_principals):
        return _verdict(
            Decision.HALT,
            Reversibility.UNKNOWN,
            "This human principal is not authorized to delegate this action.",
            "allowed_human_principals",
            action,
        )

    if not value_in_scope(context.environment.value, {item.value for item in policy.allowed_environments}):
        return _verdict(
            Decision.HALT,
            Reversibility.UNKNOWN,
            "This environment is outside the confirmed policy scope.",
            "allowed_environments",
            action,
        )

    if not value_in_scope(context.asset_id, policy.allowed_asset_ids):
        return _verdict(
            Decision.HALT,
            Reversibility.UNKNOWN,
            "This target asset is outside the confirmed policy scope.",
            "allowed_asset_ids",
            action,
        )

    if not criticality_in_scope(context.asset_criticality, policy.max_asset_criticality):
        return _verdict(
            Decision.HALT,
            Reversibility.UNKNOWN,
            "The target asset exceeds the policy's criticality ceiling.",
            "max_asset_criticality",
            action,
        )

    if action.tool not in policy.allowed_tools:
        return _verdict(
            Decision.HALT,
            Reversibility.UNKNOWN,
            "This tool is not authorized by the confirmed policy.",
            "allowed_tools",
            action,
        )

    if isinstance(action, GitHubAction):
        if not value_in_scope(action.args.operation, policy.allowed_github_operations):
            return _verdict(
                Decision.HALT,
                Reversibility.UNKNOWN,
                "The GitHub operation is not authorized by the policy.",
                "allowed_github_operations",
                action,
            )
        if not value_in_scope(action.args.repository, policy.allowed_github_repositories):
            return _verdict(
                Decision.HALT,
                Reversibility.UNKNOWN,
                "The GitHub repository is not authorized by the policy.",
                "allowed_github_repositories",
                action,
            )

    try:
        forbidden = matches_forbidden(action, policy.forbidden_patterns)
    except re.error:
        return _verdict(
            Decision.HALT,
            Reversibility.UNKNOWN,
            "The confirmed policy contains an invalid forbidden pattern.",
            "invalid_forbidden_pattern",
            action,
        )
    if forbidden is not None:
        return _verdict(
            Decision.HALT,
            Reversibility.UNKNOWN,
            "This action matches an explicitly forbidden policy pattern.",
            f"forbidden_pattern:{forbidden}",
            action,
        )

    reversibility = classify(action)
    if reversibility == Reversibility.REVERSIBLE:
        if isinstance(action, DbAction):
            if not db_op_allowed(action.args.sql, policy.allowed_db_ops):
                return _verdict(
                    Decision.HALT,
                    reversibility,
                    "The database operation is not authorized by the policy.",
                    "allowed_db_ops",
                    action,
                )
            if not db_table_allowed(action.args.sql, policy.allowed_db_tables):
                return _verdict(
                    Decision.HALT,
                    reversibility,
                    "The database table is not authorized by the policy.",
                    "allowed_db_tables",
                    action,
                )
        return _verdict(
            Decision.ALLOW,
            reversibility,
            "Recognized read-only action is authorized and can proceed.",
            "reversible",
            action,
        )

    if isinstance(action, FsWriteAction) and not path_in_scope(
        action.args.path, policy.allowed_roots
    ):
        return _verdict(
            Decision.HALT,
            reversibility,
            "The file path is outside the policy's approved sandbox roots.",
            "allowed_roots",
            action,
        )

    if isinstance(action, DbAction):
        if not db_op_allowed(action.args.sql, policy.allowed_db_ops):
            return _verdict(
                Decision.HALT,
                reversibility,
                "The database operation is not authorized by the policy.",
                "allowed_db_ops",
                action,
            )
        if not db_table_allowed(action.args.sql, policy.allowed_db_tables):
            return _verdict(
                Decision.HALT,
                reversibility,
                "The database table is not authorized by the policy.",
                "allowed_db_tables",
                action,
            )

    if isinstance(action, TransferAction) and not within_spend(
        context.spent_cents,
        action.args.cents,
        policy.spend_cap_cents,
    ):
        return _verdict(
            Decision.HALT,
            reversibility,
            "The transfer would exceed the policy's cumulative spending cap.",
            "spend_cap",
            action,
        )

    return _verdict(
        Decision.ESCALATE,
        reversibility,
        "This irreversible action is in scope and requires explicit approval.",
        "irreversible_in_scope",
        action,
    )


def _verdict(
    decision: Decision,
    reversibility: Reversibility,
    reason: str,
    matched_rule: str,
    action: ProposedAction,
) -> Verdict:
    """Construct a fully populated audit verdict."""

    return Verdict(
        decision=decision,
        reversibility=reversibility,
        reason=reason,
        matched_rule=matched_rule,
        action=action,
    )
