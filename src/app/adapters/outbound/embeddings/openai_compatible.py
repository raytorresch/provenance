from openai import OpenAI

from app.adapters.outbound.embeddings.provider import build_client
from app.core.config import Settings


class OpenAICompatibleEmbedder:
    def __init__(self, client: OpenAI, model_name: str) -> None:
        self._client = client
        self._model_name = model_name

    @classmethod
    def from_settings(cls, settings: Settings) -> OpenAICompatibleEmbedder:
        # settings.EMBEDDING_PROVIDER is already an EmbeddingProvider:
        # Settings validates it at construction time.
        client = build_client(
            settings.EMBEDDING_PROVIDER,
            settings.EMBEDDING_API_KEY,
            settings.EMBEDDING_BASE_URL,
        )

        return cls(client, settings.EMBEDDING_MODEL)

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=self._model_name, input=texts)
        return [d.embedding for d in response.data]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]
