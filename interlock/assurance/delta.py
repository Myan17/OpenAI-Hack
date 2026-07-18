"""Deterministic semantic comparison for agent authority surfaces."""

from interlock.assurance.models import AuthorityDelta, AuthoritySurface


def _added(before: tuple[str, ...], after: tuple[str, ...]) -> tuple[str, ...]:
    """Return stable capabilities present only in the candidate authority."""

    return tuple(sorted(set(after) - set(before)))


def _removed(before: tuple[str, ...], after: tuple[str, ...]) -> tuple[str, ...]:
    """Return stable capabilities removed from the candidate authority."""

    return tuple(sorted(set(before) - set(after)))


def compare_authority(baseline: AuthoritySurface, candidate: AuthoritySurface) -> AuthorityDelta:
    """Compare typed authority facts without executing an agent or adapter."""

    return AuthorityDelta(
        added_principals=_added(baseline.principals, candidate.principals),
        removed_principals=_removed(baseline.principals, candidate.principals),
        added_tools=_added(baseline.tools, candidate.tools),
        removed_tools=_removed(baseline.tools, candidate.tools),
        added_filesystem_roots=_added(baseline.filesystem_roots, candidate.filesystem_roots),
        removed_filesystem_roots=_removed(baseline.filesystem_roots, candidate.filesystem_roots),
        added_db_operations=_added(baseline.db_operations, candidate.db_operations),
        removed_db_operations=_removed(baseline.db_operations, candidate.db_operations),
        added_db_tables=_added(baseline.db_tables, candidate.db_tables),
        removed_db_tables=_removed(baseline.db_tables, candidate.db_tables),
        added_github_operations=_added(baseline.github_operations, candidate.github_operations),
        removed_github_operations=_removed(baseline.github_operations, candidate.github_operations),
        added_github_repositories=_added(baseline.github_repositories, candidate.github_repositories),
        removed_github_repositories=_removed(baseline.github_repositories, candidate.github_repositories),
        added_environments=_added(baseline.environments, candidate.environments),
        removed_environments=_removed(baseline.environments, candidate.environments),
        spend_cap_increase_cents=max(0, candidate.spend_cap_cents - baseline.spend_cap_cents),
        approval_requirement_removed=(
            baseline.irreversible_actions_require_approval
            and not candidate.irreversible_actions_require_approval
        ),
    )
