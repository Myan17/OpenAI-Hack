"""Tests for deriving assurance manifests from the existing typed policy."""

from interlock.assurance.capture import manifest_from_policy
from interlock.engine.models import Environment, Policy


def test_manifest_capture_preserves_policy_authority_and_unscoped_dimensions() -> None:
    policy = Policy(
        task="inspect API issue",
        allowed_tools={"github", "inspect"},
        allowed_db_ops={"SELECT"},
        allowed_db_tables={"sessions"},
        allowed_agent_ids={"release-agent"},
        allowed_environments={Environment.STAGING},
        allowed_github_operations={"read_issue"},
        allowed_github_repositories={"acme/api"},
        spend_cap_cents=25,
    )

    manifest = manifest_from_policy(
        policy,
        release_id="candidate-18",
        source="local-policy",
        components={"policy": "a" * 64},
    )

    assert manifest.authority.tools == ("github", "inspect")
    assert manifest.authority.principals == ("agent:release-agent",)
    assert manifest.authority.environments == ("staging",)
    assert manifest.authority.github_operations == ("read_issue",)
    assert manifest.authority.unrestricted_dimensions == ("asset_ids", "human_principals")

