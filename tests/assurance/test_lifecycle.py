"""Tests for expiry, retirement, and auditability of assurance memory."""

from pathlib import Path

import pytest

from interlock.assurance.store import AssuranceStore


def test_expired_active_case_is_excluded_from_replay_and_recorded(tmp_path: Path) -> None:
    store = AssuranceStore(tmp_path / "events.sqlite")
    candidate = store.create_candidate(
        title="Short-lived case",
        summary="A reviewed fixture expires deterministically.",
        source="event:18",
        owner="qa@example.test",
        expires_at_epoch=10,
    )
    store.review_candidate(candidate.case_id, "approved", reviewer="reviewer@example.test")

    assert [case.case_id for case in store.active_cases(now_epoch=10)] == [candidate.case_id]
    assert store.active_cases(now_epoch=11) == []
    assert store.case(candidate.case_id).status == "expired"
    assert [event["action"] for event in store.audit_events(candidate.case_id)] == [
        "created", "approved", "expired"
    ]


def test_active_case_can_be_retired_once_and_never_reactivated_by_review(tmp_path: Path) -> None:
    store = AssuranceStore(tmp_path / "events.sqlite")
    candidate = store.create_candidate(
        title="Retire case",
        summary="A stale case can be deliberately removed.",
        source="event:19",
        owner="qa@example.test",
    )
    store.review_candidate(candidate.case_id, "approved", reviewer="reviewer@example.test")

    retired = store.retire_case(candidate.case_id, actor="owner@example.test")

    assert retired is not None
    assert retired.status == "retired"
    assert store.review_candidate(candidate.case_id, "approved", reviewer="reviewer@example.test") is None
    assert store.active_cases() == []


def test_candidate_summary_with_email_like_pii_is_rejected_before_storage(tmp_path: Path) -> None:
    store = AssuranceStore(tmp_path / "events.sqlite")

    with pytest.raises(ValueError, match="sensitive"):
        store.create_candidate(
            title="PII incident",
            summary="Customer alice@example.com appeared in an unsafe action.",
            source="event:20",
            owner="qa@example.test",
        )
