import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from dotenv import dotenv_values, load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
_ENV_FILE = ROOT_DIR / ".env"


def _merge_dotenv_into_environ(path: Path) -> None:
    """
    Copy values from .env into os.environ when the variable is missing or blank.

    Fixes: `load_dotenv(override=False)` ignores .env if the shell exported an
    empty OPENAI_API_KEY, which is a common cause of 503 in local dev.
    """
    if not path.is_file():
        return
    for key, raw in dotenv_values(path, interpolate=False).items():
        if raw is None:
            continue
        val = raw.strip()
        if val == "":
            continue
        cur = os.environ.get(key)
        if cur is None or (isinstance(cur, str) and cur.strip() == ""):
            os.environ[key] = val


_merge_dotenv_into_environ(_ENV_FILE)
load_dotenv(_ENV_FILE, override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: Optional[str] = None
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_mode: str = "embedding-3-small"
    log_level: str = "INFO"
    knowledge_base_path: Path = DATA_DIR / "knowledge_base.json"
    faiss_index_path: Path = DATA_DIR / "faiss.index"
    faiss_meta_path: Path = DATA_DIR / "faiss_meta.json"

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def normalize_openai_api_key(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        if isinstance(v, str):
            return v.strip()
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
