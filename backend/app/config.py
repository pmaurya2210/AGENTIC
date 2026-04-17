from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    max_input_chars: int = Field(default=120000, alias="MAX_INPUT_CHARS")
    chunk_chars: int = Field(default=4000, alias="CHUNK_CHARS")
    chunk_overlap: int = Field(default=200, alias="CHUNK_OVERLAP")
    max_parallel_chunks: int = Field(default=4, alias="MAX_PARALLEL_CHUNKS")
    openai_call_timeout_seconds: int = Field(default=40, alias="OPENAI_CALL_TIMEOUT_SECONDS")
    openai_max_retries: int = Field(default=3, alias="OPENAI_MAX_RETRIES")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
