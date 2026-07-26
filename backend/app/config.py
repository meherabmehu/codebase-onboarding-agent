"""
Centralized settings. Loaded once from .env via pydantic-settings.
Everything downstream (agents, indexer, ingestor) reads from `settings`.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    anthropic_api_key: str = ""
    claude_model_strong: str = "claude-sonnet-4-6"
    claude_model_fast: str = "claude-haiku-4-5-20251001"

    #Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash-001"

    #GROQ
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # GitHub
    github_token: str = ""

    # Embeddings
    voyage_api_key: str = ""
    voyage_model: str = "voyage-code-2"

    # Vector DB
    vector_db: str = "chroma"  # "chroma" | "qdrant"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    # App
    data_dir: str = "./data"
    max_repo_size_mb: int = 500
    max_commits_to_index: int = 2000


settings = Settings()