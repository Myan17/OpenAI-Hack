"""Compatibility checks for public routes required by the current local demo."""

from fastapi.testclient import TestClient

from interlock.api.eventlog import EventLog
from interlock.api.main import create_app


def test_required_demo_and_assurance_routes_remain_available(tmp_path) -> None:
    app = create_app(EventLog(tmp_path / "events.sqlite"))
    routes = {route.path for route in app.routes}

    assert {
        "/health",
        "/policy",
        "/events",
        "/runs",
        "/simulate",
        "/demo",
        "/assurance/diff",
        "/assurance/candidates",
        "/assurance/replay",
        "/assurance/report",
        "/assurance/verify",
    }.issubset(routes)
    assert TestClient(app).get("/health").json() == {"status": "ok"}
