from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GHOSTCONTEXT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    upstream_base_url: str = Field(
        default="http://127.0.0.1:1234/v1",
        description="OpenAI-compatible base URL of the real LLM",
    )
    upstream_api_key: str = Field(
        default="not-needed",
        description="API key sent to the upstream (LM Studio often ignores it)",
    )

    host: str = "0.0.0.0"
    port: int = 8000

    log_dir: Path = Path("context_logs")
    chroma_path: Path = Path("chroma_data")
    collection_name: str = "ghostcontext_history"

    n_results: int = Field(default=3, ge=1, le=20)
    proxy_model_id: str = "ghostcontext"
    default_upstream_model: str | None = Field(
        default=None,
        description="If set, used when the client omits model in the request body",
    )


def load_settings() -> Settings:
    return Settings()
