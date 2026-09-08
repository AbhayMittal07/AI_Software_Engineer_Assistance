"""Supervisor/uvicorn entrypoint shim: `uvicorn server:app`."""
from app.main import app

__all__ = ["app"]
