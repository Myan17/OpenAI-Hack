"""Tests for the additive developer-agent change-control domain models."""

import pytest
from pydantic import ValidationError

from interlock.assurance.models import AuthoritySurface, ChangeManifest


def test_manifest_digest_is_stable_for_equivalent_unordered_authority() -> None:
    first = ChangeManifest(
        release_id="candidate-17",
        source="local-fixture",
        components={"policy": "b" * 64, "adapter": "a" * 64},
        authority=AuthoritySurface(
            principals=["human:myan", "agent:demo"],
            tools=["inspect", "github"],
            db_operations=["SELECT", "UPDATE"],
        ),
    )
    second = ChangeManifest(
        release_id="candidate-17",
        source="local-fixture",
        components={"adapter": "a" * 64, "policy": "b" * 64},
        authority=AuthoritySurface(
            principals=["agent:demo", "human:myan"],
            tools=["github", "inspect"],
            db_operations=["UPDATE", "SELECT"],
        ),
    )

    assert first.canonical_json() == second.canonical_json()
    assert first.digest == second.digest


def test_manifest_rejects_unknown_fields_and_invalid_component_digest() -> None:
    with pytest.raises(ValidationError):
        ChangeManifest.model_validate(
            {
                "release_id": "candidate-17",
                "source": "local-fixture",
                "components": {"policy": "not-a-digest"},
                "authority": {},
                "surprise": "not allowed",
            }
        )
