from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import EmbeddingProvider, Settings


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "_env_file": None,
        "VECTOR_DB_URL": "postgresql://test:test@localhost:5432/test",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_embedding_provider_rejects_an_unknown_value_at_construction() -> None:
    # Typed as the enum, not str: an unknown provider fails Settings
    # construction (app startup) instead of only surfacing the first time
    # something calls build_client() with it.
    with pytest.raises(ValidationError, match="EMBEDDING_PROVIDER"):
        _settings(EMBEDDING_PROVIDER="not-a-real-provider")


def test_embedding_provider_accepts_each_known_value_and_coerces_to_the_enum() -> None:
    for raw, expected in [
        ("openai", EmbeddingProvider.OPENAI),
        ("gemini", EmbeddingProvider.GEMINI),
        ("lmstudio", EmbeddingProvider.LMSTUDIO),
    ]:
        assert _settings(EMBEDDING_PROVIDER=raw).EMBEDDING_PROVIDER is expected


def test_embedding_provider_defaults_to_openai() -> None:
    assert _settings().EMBEDDING_PROVIDER is EmbeddingProvider.OPENAI


def test_settings_has_no_separate_openai_api_key_field() -> None:
    # OPENAI_API_KEY used to be its own field, duplicating EMBEDDING_API_KEY
    # with the same credential under a second name. Now OPENAI_API_KEY is
    # only an env var name EMBEDDING_API_KEY can fall back to, not a second
    # stored field.
    assert "OPENAI_API_KEY" not in Settings.model_fields


def test_embedding_api_key_falls_back_to_the_openai_api_key_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "legacy-key")
    monkeypatch.delenv("EMBEDDING_API_KEY", raising=False)

    assert _settings().EMBEDDING_API_KEY == "legacy-key"


def test_embedding_api_key_prefers_its_own_env_var_over_the_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "legacy-key")
    monkeypatch.setenv("EMBEDDING_API_KEY", "dedicated-key")

    assert _settings().EMBEDDING_API_KEY == "dedicated-key"
