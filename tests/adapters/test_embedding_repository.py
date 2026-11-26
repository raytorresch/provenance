from __future__ import annotations

from dataclasses import dataclass

from app.adapters.outbound.embeddings.provider import EmbeddingProvider
from app.adapters.outbound.embeddings.repositories import (
    embedding_repository as embedding_repository_module,
)
from app.adapters.outbound.embeddings.repositories.embedding_repository import (
    OpenAICompatibleEmbeddingRepository,
)
from app.core.config import Settings


@dataclass
class _FakeEmbeddingDatum:
    embedding: list[float]


@dataclass
class _FakeEmbeddingResponse:
    data: list[_FakeEmbeddingDatum]


class _FakeEmbeddingsResource:
    def __init__(self) -> None:
        self.received_model: str | None = None
        self.received_input: list[str] | None = None

    def create(self, model: str, input: list[str]) -> _FakeEmbeddingResponse:
        self.received_model = model
        self.received_input = input
        return _FakeEmbeddingResponse(
            data=[_FakeEmbeddingDatum(embedding=[float(len(text))]) for text in input]
        )


class _FakeOpenAIClient:
    def __init__(self) -> None:
        self.embeddings = _FakeEmbeddingsResource()


def test_embed_texts_sends_model_and_texts_and_returns_vectors() -> None:
    client = _FakeOpenAIClient()
    repo = OpenAICompatibleEmbeddingRepository(client, "fake-model")

    vectors = repo.embed_texts(["ab", "abcd"])

    assert client.embeddings.received_model == "fake-model"
    assert client.embeddings.received_input == ["ab", "abcd"]
    assert vectors == [[2.0], [4.0]]


def test_embed_query_embeds_a_single_text_and_unwraps_the_result() -> None:
    client = _FakeOpenAIClient()
    repo = OpenAICompatibleEmbeddingRepository(client, "fake-model")

    vector = repo.embed_query("abc")

    assert client.embeddings.received_input == ["abc"]
    assert vector == [3.0]


def test_model_name_property_exposes_the_configured_model() -> None:
    repo = OpenAICompatibleEmbeddingRepository(_FakeOpenAIClient(), "fake-model")

    assert repo.model_name == "fake-model"


def test_from_settings_wires_provider_api_key_base_url_and_model(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_build_client(provider, api_key, base_url):
        captured["provider"] = provider
        captured["api_key"] = api_key
        captured["base_url"] = base_url
        return _FakeOpenAIClient()

    monkeypatch.setattr(embedding_repository_module, "build_client", fake_build_client)

    settings = Settings(
        EMBEDDING_PROVIDER="lmstudio",
        EMBEDDING_API_KEY="setting-key",
        EMBEDDING_BASE_URL="http://localhost:1234/v1",
        EMBEDDING_MODEL="local-embed-model",
    )

    repo = OpenAICompatibleEmbeddingRepository.from_settings(settings)

    assert captured["provider"] == EmbeddingProvider.LMSTUDIO
    assert captured["api_key"] == "setting-key"
    assert captured["base_url"] == "http://localhost:1234/v1"
    assert repo.model_name == "local-embed-model"
