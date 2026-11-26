from openai import OpenAI

from app.core.config import EmbeddingProvider

_DEFAULT_BASE_URLS = {
    EmbeddingProvider.GEMINI: "https://generativelanguage.googleapis.com/v1beta/openai/",
    EmbeddingProvider.LMSTUDIO: "http://localhost:1234/v1",
}


def build_client(
    provider: EmbeddingProvider, api_key: str | None, base_url: str | None
) -> OpenAI:
    return OpenAI(
        api_key=api_key, base_url=base_url or _DEFAULT_BASE_URLS.get(provider)
    )
