"""Declarative base + import semua model agar terdaftar di metadata (dipakai Alembic)."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Impor model di bawah base agar Alembic autogenerate melihat seluruh tabel.
from app.db import models  # noqa: E402,F401
