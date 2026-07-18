"""Tests for the safe, reviewer-governed assurance failure-memory store."""

from pathlib import Path

import pytest

from interlock.assurance.store import AssuranceStore


def test_candidate_case_is_inactive_until_explicit_review_approval(tmp_path: Path) -> None:
    store = AssuranceStore(tmp_path / "events.sqlite")

    candidate = store.create_candidate(
        title="Block destructive table drop",
        summary="Observed a deterministic halt for DROP TABLE users.",
        source="event:12",
        owner="security@example.test",
    )

    assert candidate.status == "pending_review"
    assert store.active_cases() == []

    approved = store.review_candidate(candidate.case_id, "approved", reviewer="reviewer@example.test")

    assert approved is not None
    assert approved.status == "active"
    assert [case.case_id for case in store.active_cases()] == [candidate.case_id]


def test_candidate_case_with_secret_like_payload_is_rejected_before_persistence(tmp_path: Path) -> None:
    store = AssuranceStore(tmp_path / "events.sqlite")

    with pytest.raises(ValueError, match="secret-like"):
        store.create_candidate(
            title="Leaked credential",
            summary="OPENAI_API_KEY=sk-this-must-not-be-stored",
            source="event:13",
            owner="security@example.test",
        )

    assert store.all_cases() == []


def test_candidate_review_is_single_use_and_auditable(tmp_path: Path) -> None:
    store = AssuranceStore(tmp_path / "events.sqlite")
    candidate = store.create_candidate(
        title="Verify migration approval",
        summary="A migration must remain an escalation.",
        source="event:14",
        owner="qa@example.test",
    )

    assert store.review_candidate(candidate.case_id, "rejected", reviewer="qa@example.test") is not None
    assert store.review_candidate(candidate.case_id, "approved", reviewer="qa@example.test") is None
