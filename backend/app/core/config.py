"""Application configuration, loaded from environment / .env via pydantic-settings."""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Application ──────────────────────────────────────────────────────────
    environment: str = "development"
    api_v1_prefix: str = "/api"
    # NoDecode: let the validator below split a comma-separated string itself,
    # instead of pydantic-settings trying to JSON-decode the env value first.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    # Regex alternative to the explicit list — handy when the frontend origin
    # varies (e.g. Vercel preview/per-deploy URLs). Empty disables it.
    cors_origin_regex: str = ""

    # ── Security / JWT ───────────────────────────────────────────────────────
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Allow passwordless "guest" login in production: each call provisions a
    # fresh, isolated anonymous account (clean slate per new visitor). Off by
    # default; enable for a public demo that shouldn't require GitHub OAuth.
    allow_guest_login: bool = False

    # ── GitHub OAuth ─────────────────────────────────────────────────────────
    github_client_id: str = ""
    github_client_secret: str = ""
    github_oauth_redirect_uri: str = "http://localhost:5173/login/callback"

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "postgresql+psycopg://codeatreus:codeatreus@localhost:5432/codeatreus"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle: int = 1800

    # ── Redis / Celery ───────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── Vector store ─────────────────────────────────────────────────────────
    chroma_persist_dir: str = "./data/chroma"
    chroma_mode: str = "local"  # "local" (file) or "http" (server)
    chroma_host: str = "chroma"
    chroma_port: int = 8000

    # ── Embeddings ───────────────────────────────────────────────────────────
    embedding_provider: str = "fastembed"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    jina_api_key: str = ""

    # ── LLM (OpenRouter) ─────────────────────────────────────────────────────
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "nvidia/nemotron-3.5-lightning:free"

    # ── Clone / index guardrails ─────────────────────────────────────────────
    clone_dir: str = "./data/repos"
    max_repo_size_mb: int = 200
    max_file_size_kb: int = 1024
    clone_timeout_seconds: int = 120

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, v: object) -> object:
        """Accept a comma-separated string from the environment."""
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton (safe to import anywhere)."""
    return Settings()


settings = get_settings()
