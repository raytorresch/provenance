from enum import StrEnum
from functools import lru_cache

from pydantic import AliasChoices, AliasPath, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbeddingProvider(StrEnum):
    OPENAI = "openai"
    GEMINI = "gemini"
    LMSTUDIO = "lmstudio"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = Field(
        default="Provenance",
        validation_alias=AliasChoices("PROJECT_NAME", AliasPath("project", "name")),
    )
    VERSION: str = Field(
        default="1.0.0",
        validation_alias=AliasChoices("VERSION", AliasPath("project", "version")),
    )
    API_V1_STR: str = Field(
        default="/api/v1",
        validation_alias=AliasChoices("API_V1_STR", AliasPath("project", "api_v1_str")),
    )

    ENVIRONMENT: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", AliasPath("environment")),
    )

    # Required: no default. Without a real DB URL the app must fail fast at
    # startup with a clear validation error, not limp along with None.
    VECTOR_DB_URL: str = Field(
        validation_alias=AliasChoices("VECTOR_DB_URL", AliasPath("database", "url")),
    )

    # EMBEDDING_PROVIDER is typed as the enum (not str) so an unknown value
    # fails Settings construction at startup, instead of only surfacing the
    # first time something calls build_client() with it.
    EMBEDDING_PROVIDER: EmbeddingProvider = Field(default=EmbeddingProvider.OPENAI)
    # No separate OPENAI_API_KEY field: it used to duplicate this one,
    # holding the same credential under a second name. OPENAI_API_KEY is
    # still accepted as the env var name, as a fallback alias, not as its
    # own stored field.
    EMBEDDING_API_KEY: str | None = Field(
        default=None,
        validation_alias=AliasChoices("EMBEDDING_API_KEY", "OPENAI_API_KEY"),
    )
    EMBEDDING_BASE_URL: str | None = Field(default=None)
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")


@lru_cache
def get_settings() -> Settings:
    return Settings()
