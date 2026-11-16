from functools import lru_cache

from pydantic import AliasChoices, AliasPath, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    VECTOR_DB_URL: str = Field(
        default=None,
        validation_alias=AliasChoices("VECTOR_DB_URL", AliasPath("database", "url")),
    )

    OPENAI_API_KEY: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "OPENAI_API_KEY",
            AliasPath("project", "openai_api_key"),
        ),
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()