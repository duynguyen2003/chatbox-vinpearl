from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM
    llm_provider: str = "gemini"
    llm_model: str = "gemini/gemini-2.0-flash"
    llm_api_key: str | None = None
    llm_api_key_backup: str | None = None
    llm_base_url: str | None = None

    llm_temperature: float = 0.2
    llm_max_tokens: int = 1500
    llm_timeout: float = 60.0
    llm_max_retries: int = 2

    # Local embedding
    local_embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_device: str = "cpu"
    embedding_batch_size: int = 128

    # Database
    database_url: str = (
        "postgresql+pg8000://vinpearl:vinpearl@localhost:5432/vinpearl"
    )
    db_echo: bool = False

    # Data
    data_dir: Path = Path("./data")
    chroma_dir: Path = Path("./storage/chroma_local")
    chroma_collection: str = "vinpearl_multilingual_e5_small"
    ticket_file: Path = Path("./storage/tickets.jsonl")
    chat_history_file: Path = Path("./storage/chat_history.jsonl")

    # Conversation memory
    memory_enabled: bool = True
    memory_max_turns: int = 16
    memory_max_chars: int = 12000

    # RAG
    top_k: int = 10
    max_context_chars: int = 18000
    min_relevance_score: float = 0.35

    # Authentication
    auth_session_days: int = 7
    password_pbkdf2_iterations: int = 600000
    admin_bootstrap_key: str | None = None

    # API
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
