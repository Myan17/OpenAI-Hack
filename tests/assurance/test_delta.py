"""Tests for semantic authority comparisons used by report-only assurance."""

from interlock.assurance.delta import compare_authority
from interlock.assurance.models import AuthoritySurface


def test_compare_authority_reports_new_write_capability_as_an_expansion() -> None:
    baseline = AuthoritySurface(tools=["inspect"], db_operations=["SELECT"], spend_cap_cents=0)
    candidate = AuthoritySurface(
        tools=["inspect", "db"],
        db_operations=["SELECT", "UPDATE"],
        spend_cap_cents=500,
    )

    delta = compare_authority(baseline, candidate)

    assert delta.has_expansion is True
    assert delta.added_tools == ("db",)
    assert delta.added_db_operations == ("UPDATE",)
    assert delta.spend_cap_increase_cents == 500


def test_compare_authority_does_not_treat_narrowing_as_an_expansion() -> None:
    baseline = AuthoritySurface(tools=["inspect", "db"], db_operations=["SELECT", "UPDATE"], spend_cap_cents=500)
    candidate = AuthoritySurface(tools=["inspect"], db_operations=["SELECT"], spend_cap_cents=0)

    delta = compare_authority(baseline, candidate)

    assert delta.has_expansion is False
    assert delta.removed_tools == ("db",)
    assert delta.removed_db_operations == ("UPDATE",)
    assert delta.spend_cap_increase_cents == 0
