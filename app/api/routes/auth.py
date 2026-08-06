"""Endpoint autentikasi (TRD Bab 8)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import authenticate_user, get_current_user
from app.core.security import create_access_token
from app.db import models
from app.db.session import get_db
from app.schemas.auth import TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(db, form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Username atau password salah"
        )
    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token, role=user.role, nama=user.nama)


@router.get("/me", response_model=UserOut)
def me(user: models.User = Depends(get_current_user)) -> models.User:
    return user
