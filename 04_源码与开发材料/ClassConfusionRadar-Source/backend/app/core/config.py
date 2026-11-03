"""
本文件的作用是：读取并集中管理数据库、隐私、上传和分析相关运行配置。
"""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    debug: bool = True
    project_name: str = "Class Confusion Radar"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/class_confusion_radar"
    storage_dir: str = str(BACKEND_DIR / "storage" / "uploads")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    ai_provider: str = "offline"
    ai_model: str = "gpt-4o-mini"
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    anonymize_students: bool = True
    privacy_salt: str = "class-confusion-radar-local"
    max_dataset_zip_mb: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
