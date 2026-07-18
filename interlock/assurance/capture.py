"""Typed extraction of a report-only manifest from the current policy model."""

from interlock.assurance.models import AuthoritySurface, ChangeManifest
from interlock.engine.models import Policy


def manifest_from_policy(
    policy: Policy,
    *,
    release_id: str,
    source: str,
    components: dict[str, str],
    captured_at_epoch: int = 0,
) -> ChangeManifest:
    """Create a canonical assurance manifest without changing engine behavior."""

    unrestricted_dimensions: list[str] = []
    if not policy.allowed_human_principals:
        unrestricted_dimensions.append("human_principals")
    if not policy.allowed_asset_ids:
        unrestricted_dimensions.append("asset_ids")
    if not policy.allowed_github_operations:
        unrestricted_dimensions.append("github_operations")
    if not policy.allowed_github_repositories:
        unrestricted_dimensions.append("github_repositories")
    if not policy.allowed_environments:
        unrestricted_dimensions.append("environments")
    if not policy.allowed_agent_ids:
        unrestricted_dimensions.append("agent_ids")

    principals = [f"agent:{agent_id}" for agent_id in policy.allowed_agent_ids]
    principals.extend(f"human:{principal}" for principal in policy.allowed_human_principals)
    return ChangeManifest(
        release_id=release_id,
        source=source,
        captured_at_epoch=captured_at_epoch,
        components=components,
        authority=AuthoritySurface(
            principals=principals,
            tools=policy.allowed_tools,
            filesystem_roots=policy.allowed_roots,
            db_operations=policy.allowed_db_ops,
            db_tables=policy.allowed_db_tables,
            github_operations=policy.allowed_github_operations,
            github_repositories=policy.allowed_github_repositories,
            environments=[environment.value for environment in policy.allowed_environments],
            unrestricted_dimensions=unrestricted_dimensions,
            spend_cap_cents=policy.spend_cap_cents,
            irreversible_actions_require_approval=True,
        ),
    )
