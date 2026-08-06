"""Konfigurasi aplikasi, dibaca dari environment / berkas .env."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "DSS Bansos Bontoramba"
    app_env: str = "development"

    # Keamanan (default dev; WAJIB diganti di produksi via .env)
    secret_key: str = "dev-only-secret-change-me-in-production-0123456789"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # Database — default SQLite untuk dev lokal tanpa setup.
    database_url: str = "sqlite:///./bansos_dss.db"

    # Artefak model (diisi saat Fase 2/3/4)
    indobert_model_path: str = "ml/artifacts/indobert"
    ml_model_path: str = "ml/artifacts/classifier.joblib"
    fuzzy_config_path: str = "config/fuzzy_config.yaml"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
