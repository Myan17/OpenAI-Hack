from fastapi import FastAPI

from interlock.api.main import app


def test_default_asgi_app_is_exported_for_uvicorn() -> None:
    assert isinstance(app, FastAPI)
