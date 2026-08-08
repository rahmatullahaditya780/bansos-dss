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
    indobert_max_length: int = 128  # panjang token maksimum narasi (Tier 1)
    ml_model_path: str = "ml/artifacts/tier2"  # direktori artefak Tier 2 (model.joblib + metadata)
    fuzzy_config_path: str = "config/fuzzy_config.yaml"

    # Muat artefak model saat aplikasi start, bukan saat permintaan pertama (Fase 5, D-02).
    # Startup jadi ~14 detik lebih lama, tetapi tidak ada petugas yang menanggungnya — dan
    # metrik NFR-01 berhenti mencatat biaya pemuatan sebagai kegagalan.
    # Dimatikan di lingkungan tes agar suite tidak memuat IndoBERT sebelum tes pertama.
    panaskan_model_saat_start: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
