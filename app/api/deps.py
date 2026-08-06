"""Dependency FastAPI: autentikasi & otorisasi peran (RBAC)."""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token, verify_password
from app.db import models
from app.db.session import get_db

COOKIE_NAME = "access_token"


def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    user = db.execute(
        select(models.User).where(models.User.username == username)
    ).scalar_one_or_none()
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        return None
    return user


def _extract_token(request: Request) -> Optional[str]:
    # Prioritas header Authorization: Bearer (API/Swagger), lalu cookie (browser).
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.cookies.get(COOKIE_NAME)


def _user_from_token(request: Request, db: Session) -> Optional[models.User]:
    token = _extract_token(request)
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    user = db.get(models.User, int(payload["sub"]))
    if not user or not user.is_active:
        return None
    return user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    """Wajib terautentikasi (untuk endpoint API); 401 bila tidak."""
    user = _user_from_token(request, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tidak terautentikasi",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_petugas(user: models.User = Depends(get_current_user)) -> models.User:
    """Hanya peran petugas (FR-04)."""
    if user.role != models.Role.PETUGAS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses khusus petugas")
    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> Optional[models.User]:
    """Versi non-raising untuk halaman HTML (redirect ke login bila None)."""
    return _user_from_token(request, db)
