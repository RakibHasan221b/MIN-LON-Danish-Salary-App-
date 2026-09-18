"""Deployment hardening: CORS origins must come from CORS_ALLOWED_ORIGINS,
never default to a wildcard. See docs/deployment.md."""
import importlib
import os

from api.main import _load_cors_allowed_origins


def test_defaults_to_localhost_dev_origins_when_unset(monkeypatch):
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    origins = _load_cors_allowed_origins()
    assert "http://localhost:3000" in origins
    assert "*" not in origins


def test_reads_comma_separated_origins_from_env(monkeypatch):
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://min-loen.vercel.app, https://www.min-loen.dk",
    )
    origins = _load_cors_allowed_origins()
    assert origins == ["https://min-loen.vercel.app", "https://www.min-loen.dk"]
    assert "*" not in origins


def test_blank_env_value_falls_back_to_dev_defaults(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "   ")
    origins = _load_cors_allowed_origins()
    assert "http://localhost:3000" in origins
