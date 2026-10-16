"""
Pruebas de las utilidades de seguridad (app/security.py): CORS, API key de
administración, rate limiting y validación geográfica.
"""
import pytest
from fastapi import HTTPException

from app.security import (
    get_allowed_origins,
    rate_limit,
    reset_rate_limiter,
    validate_peru_coords,
)


def test_validate_peru_coords_accepts_cajamarca():
    validate_peru_coords(-7.16, -78.50)  # no debe lanzar


def test_validate_peru_coords_rejects_outside():
    with pytest.raises(HTTPException) as exc:
        validate_peru_coords(40.0, -3.0)  # Madrid
    assert exc.value.status_code == 422


def test_default_origins_are_local(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    origins = get_allowed_origins()
    assert origins and all(o.startswith("http") for o in origins)
    assert "http://127.0.0.1:5050" in origins


def test_origins_star(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "*")
    assert get_allowed_origins() == ["*"]


def test_origins_custom_list(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://a.com, https://b.com")
    assert get_allowed_origins() == ["https://a.com", "https://b.com"]


class _FakeRequest:
    class client:  # noqa: N801 - atributo esperado por Starlette
        host = "203.0.113.5"


def test_rate_limit_blocks_after_max_calls():
    reset_rate_limiter()
    dependency = rate_limit(max_calls=2, window_seconds=60)

    dependency(_FakeRequest())
    dependency(_FakeRequest())
    with pytest.raises(HTTPException) as exc:
        dependency(_FakeRequest())
    assert exc.value.status_code == 429
