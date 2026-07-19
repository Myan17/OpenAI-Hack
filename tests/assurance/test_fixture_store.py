"""Tests binding approved assurance memory to isolated replay fixtures."""

from pathlib import Path

import pytest

from interlock.assurance.store import AssuranceStore
from interlock.engine.models import EnforcementContext, InspectAction, InspectArgs, Policy
from interlock.engine.simulator import SimulationStep


def test_only_active_case_can_attach_and_execute_a_replay_fixture(tmp_path: Path) -> None:
    store = AssuranceStore(tmp_path / "events.sqlite")
    candidate = store.create_candidate(
        title="Preserve read-only path",
        summary="The ledger read remains safe.",
        source="event:15",
        owner="qa@example.test",
    )
    policy = Policy(task="inspect", allowed_tools={"inspect"})
    steps = [
        SimulationStep(
            id="read-ledger",
            description="Read the ledger.",
            expected_safe=True,
            action=InspectAction(args=InspectArgs(resource="ledger")),
            context=EnforcementContext(),
        )
    ]

    with pytest.raises(ValueError, match="active"):
        store.attach_replay_fixture(candidate.case_id, policy=policy, steps=steps)

    store.review_candidate(candidate.case_id, "approved", reviewer="reviewer@example.test")
    store.attach_replay_fixture(candidate.case_id, policy=policy, steps=steps)
    result = store.replay_active_case(candidate.case_id)

    assert result.case_id == candidate.case_id
    assert result.passed is True


def test_replay_fixture_cannot_be_attached_twice_without_explicit_replacement(tmp_path: Path) -> None:
    store = AssuranceStore(tmp_path / "events.sqlite")
    candidate = store.create_candidate(
        title="Preserve read-only path",
        summary="The ledger read remains safe.",
        source="event:16",
        owner="qa@example.test",
    )
    store.review_candidate(candidate.case_id, "approved", reviewer="reviewer@example.test")
    policy = Policy(task="inspect", allowed_tools={"inspect"})
    steps = [
        SimulationStep(
            id="read-ledger",
            description="Read the ledger.",
            expected_safe=True,
            action=InspectAction(args=InspectArgs(resource="ledger")),
            context=EnforcementContext(),
        )
    ]

    store.attach_replay_fixture(candidate.case_id, policy=policy, steps=steps)

    with pytest.raises(ValueError, match="already has"):
        store.attach_replay_fixture(candidate.case_id, policy=policy, steps=steps)


def test_assurance_snapshot_round_trips_cases_fixtures_and_audit_without_overwriting(tmp_path: Path) -> None:
    source = AssuranceStore(tmp_path / "source.sqlite")
    candidate = source.create_candidate(
        title="Portable reviewed replay",
        summary="A safe local fixture is recoverable.",
        source="event:17",
        owner="qa@example.test",
    )
    source.review_candidate(candidate.case_id, "approved", reviewer="reviewer@example.test")
    policy = Policy(task="inspect", allowed_tools={"inspect"})
    steps = [
        SimulationStep(
            id="read-ledger",
            description="Read the ledger.",
            expected_safe=True,
            action=InspectAction(args=InspectArgs(resource="ledger")),
            context=EnforcementContext(),
        )
    ]
    source.attach_replay_fixture(candidate.case_id, policy=policy, steps=steps)
    snapshot = source.export_snapshot()

    recovered = AssuranceStore(tmp_path / "recovered.sqlite")
    assert recovered.import_snapshot(snapshot) == 1
    assert recovered.all_cases()[0].model_dump() == source.all_cases()[0].model_dump()
    assert recovered.audit_events(candidate.case_id) == source.audit_events(candidate.case_id)
    assert recovered.replay_active_case(candidate.case_id).passed is True

    with pytest.raises(ValueError, match="empty store"):
        recovered.import_snapshot(snapshot)
