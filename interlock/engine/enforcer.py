"""The pure, deterministic Interlock policy decision function."""

import re

from interlock.engine.catalog import classify
from interlock.engine.models import (
    DbAction,
    Decision,
    EnforcementContext,
    FsWriteAction,
    Policy,
    ProposedAction,
    Reversibility,
    TransferAction,
    Verdict,
)
from interlock.engine.patterns import matches_forbidden
from interlock.engine.scope import (
    db_op_allowed,
    db_table_allowed,
    path_in_scope,
    within_spend,
)


def enforce(
    action: ProposedAction,
    policy: Policy,
    context: EnforcementContext,
) -> Verdict:
    """Return the deterministic verdict for one typed proposed action."""

    if action.tool not in policy.allowed_tools:
        return _verdict(
            Decision.HALT,
            Reversibility.UNKNOWN,
            "This tool is not authorized by the confirmed policy.",
            "allowed_tools",
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
