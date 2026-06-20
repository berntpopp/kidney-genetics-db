"""Tests for runtime configuration."""

from __future__ import annotations

import pytest

from kidney_genetics_mcp.config import Settings, get_settings


def test_defaults() -> None:
    settings = Settings()
    assert settings.api_base_url == "http://localhost:8000"
    assert settings.port == 8789
    assert settings.protocol_version == "2025-11-25"
    assert settings.default_response_mode == "compact"
    assert settings.max_response_chars_cap == 80000
    assert settings.rate_limit_global_rps == 10.0
    assert settings.mode_char_budgets == {
        "minimal": 4000,
        "compact": 12000,
        "standard": 24000,
        "full": 48000,
    }
    assert settings.allowed_origins == ["https://claude.ai", "https://claude.com"]


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KGDB_MCP_API_BASE_URL", "http://backend:8000")
    monkeypatch.setenv("KGDB_MCP_PORT", "9999")
    monkeypatch.setenv("KGDB_MCP_RATE_LIMIT_GLOBAL_RPS", "42.5")
    settings = Settings()
    assert settings.api_base_url == "http://backend:8000"
    assert settings.port == 9999
    assert settings.rate_limit_global_rps == 42.5


def test_csv_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "KGDB_MCP_ALLOWED_ORIGINS", "https://a.example, https://b.example ,"
    )
    settings = Settings()
    assert settings.allowed_origins == ["https://a.example", "https://b.example"]


def test_get_settings_cached() -> None:
    get_settings.cache_clear()
    first = get_settings()
    second = get_settings()
    assert first is second
