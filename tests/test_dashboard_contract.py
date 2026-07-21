"""Static dashboard smoke contract for controls that must survive additive work."""

from pathlib import Path


def test_dashboard_keeps_core_demo_and_assurance_controls() -> None:
    source = (Path(__file__).parents[1] / "web" / "app" / "page.tsx").read_text(encoding="utf-8")

    for control in (
        "Draft policy",
        "Confirm policy",
        "Run safety demo",
        "Assurance memory",
        "Attach &amp; replay fixture",
        "Release evidence",
        "Generate local evidence report",
        "Verify evidence bundle",
        "Retire case",
        "Fixture adapter preview",
        "Preview fixture callback",
    ):
        assert control in source


def test_dashboard_exposes_data_backed_operations_overview() -> None:
    source = (Path(__file__).parents[1] / "web" / "app" / "page.tsx").read_text(encoding="utf-8")

    for contract in (
        '"/health"',
        '"/assurance/health"',
        '"/assurance/metrics"',
        "Safety overview",
        "Decision volume",
        "Pending review",
        "Evidence posture",
    ):
        assert contract in source
