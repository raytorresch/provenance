from __future__ import annotations

from app.adapters.outbound.embeddings.provider import build_client
from app.core.config import EmbeddingProvider


def test_build_client_uses_explicit_base_url_over_default() -> None:
    client = build_client(
        EmbeddingProvider.GEMINI, api_key="key", base_url="https://custom.example/v1"
    )

    assert str(client.base_url) == "https://custom.example/v1/"


def test_build_client_falls_back_to_provider_default_base_url() -> None:
    client = build_client(EmbeddingProvider.GEMINI, api_key="key", base_url=None)

    assert (
        str(client.base_url)
        == "https://generativelanguage.googleapis.com/v1beta/openai/"
    )


def test_build_client_openai_has_no_default_base_url_override() -> None:
    # OPENAI isn't in _DEFAULT_BASE_URLS, so it must fall back to the
    # OpenAI SDK's own default rather than None or a KeyError.
    client = build_client(EmbeddingProvider.OPENAI, api_key="key", base_url=None)

    assert str(client.base_url) == "https://api.openai.com/v1/"


def test_build_client_lmstudio_defaults_to_local_server() -> None:
    client = build_client(EmbeddingProvider.LMSTUDIO, api_key="key", base_url=None)

    assert str(client.base_url) == "http://localhost:1234/v1/"


def test_build_client_passes_through_api_key() -> None:
    client = build_client(EmbeddingProvider.OPENAI, api_key="super-secret", base_url=None)

    assert client.api_key == "super-secret"
