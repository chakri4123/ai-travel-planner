from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    google_api_key: str = ""
    chat_model: str = "gemini-3.1-flash-lite"
    embedding_model: str = "gemini-embedding-001"
    temperature: float = 0.3
    retrieval_k: int = 4
    request_timeout_seconds: int = 90
    max_parse_attempts: int = 3
    max_budget_revisions: int = 2
    knowledge_dir: Path = ROOT / "data" / "destinations"
