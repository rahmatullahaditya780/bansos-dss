"""Rute web (HTML) — dashboard server-rendered (Jinja2 + Bootstrap + HTMX).

Autentikasi berbasis cookie (di-set saat login). Halaman butuh peran petugas; bila belum
login, dialihkan ke /login.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import COOKIE_NAME, authenticate_user, get_optional_user
from app.core.config import settings
from app.core.security import create_access_token
from app.db import models
from app.db.session import get_db
from app.schemas.pengajuan import DataSurveiIn, PengajuanCreate, TeksNaratifIn, WargaIn
from app.services import dashboard_service, pipeline
from app.services.pengajuan_service import create_pengajuan
from app.templating import templates

router = APIRouter(tags=["web"], include_in_schema=False)


def _redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=status.HTTP_303_SEE_OTHER)


def _require(user: Optional[models.User]) -> bool:
    return user is not None and user.role == models.Role.PETUGAS


# ---- Auth ----
@router.get("/", response_class=HTMLResponse)
def home(user: Optional[models.User] = Depends(get_optional_user)):
    return _redirect("/dashboard") if user else _redirect("/login")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: Optional[models.User] = Depends(get_optional_user)):
    if user:
        return _redirect("/dashboard")
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, username, password)
    if user is None:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Username atau password salah"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    token = create_access_token(user.id, user.role)
    resp = _redirect("/dashboard")
    resp.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return resp


@router.get("/logout")
def logout():
    resp = _redirect("/login")
    resp.delete_cookie(COOKIE_NAME)
    return resp


# ---- Dashboard ----
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(get_optional_user),
):
    if not _require(user):
        return _redirect("/login")
    recent = db.execute(
        select(models.Pengajuan).order_by(models.Pengajuan.tanggal.desc()).limit(8)
    ).scalars().all()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"user": user, "r": dashboard_service.ringkasan(db), "recent": recent},
    )


@router.get("/dashboard/ringkasan-partial", response_class=HTMLResponse)
def dashboard_partial(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(get_optional_user),
):
    if not _require(user):
        return HTMLResponse("", status_code=status.HTTP_401_UNAUTHORIZED)
    return templates.TemplateResponse(
        request, "partials/_ringkasan.html", {"r": dashboard_service.ringkasan(db)}
    )


# ---- Daftar pengajuan ----
@router.get("/daftar", response_class=HTMLResponse)
def daftar(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(get_optional_user),
):
    if not _require(user):
        return _redirect("/login")
    rows = db.execute(
        select(models.Pengajuan).order_by(models.Pengajuan.tanggal.desc())
    ).scalars().all()
    return templates.TemplateResponse(request, "daftar.html", {"user": user, "rows": rows})


# ---- Detail + analisis (HTMX) ----
@router.get("/detail/{pengajuan_id}", response_class=HTMLResponse)
def detail(
    pengajuan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(get_optional_user),
):
    if not _require(user):
        return _redirect("/login")
    p = db.get(models.Pengajuan, pengajuan_id)
    if p is None:
        return HTMLResponse("Pengajuan tidak ditemukan", status_code=status.HTTP_404_NOT_FOUND)
    return templates.TemplateResponse(
        request, "detail.html", {"user": user, "p": p, "hasil": pipeline.susun_hasil(p)}
    )


@router.post("/detail/{pengajuan_id}/analisis", response_class=HTMLResponse)
def detail_analisis(
    pengajuan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(get_optional_user),
):
    if not _require(user):
        return HTMLResponse("", status_code=status.HTTP_401_UNAUTHORIZED)
    p = db.get(models.Pengajuan, pengajuan_id)
    if p is None or p.data_survei is None:
        return HTMLResponse(
            "<div class='alert alert-danger'>Data survei belum lengkap.</div>",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    pipeline.analisis_pengajuan(db, p)
    db.refresh(p)
    return templates.TemplateResponse(
        request, "partials/_hasil.html", {"p": p, "hasil": pipeline.susun_hasil(p)}
    )


# ---- Ranking (HTMX) ----
@router.get("/peringkat", response_class=HTMLResponse)
def peringkat(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(get_optional_user),
):
    if not _require(user):
        return _redirect("/login")
    return templates.TemplateResponse(request, "peringkat.html", {"user": user})


@router.post("/peringkat/run", response_class=HTMLResponse)
def peringkat_run(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(get_optional_user),
):
    if not _require(user):
        return HTMLResponse("", status_code=status.HTTP_401_UNAUTHORIZED)
    hasil = pipeline.jalankan_ranking(db)
    return templates.TemplateResponse(request, "partials/_ranking_table.html", {"hasil": hasil})


# ---- Form pengajuan baru ----
@router.get("/form", response_class=HTMLResponse)
def form_page(request: Request, user: Optional[models.User] = Depends(get_optional_user)):
    if not _require(user):
        return _redirect("/login")
    return templates.TemplateResponse(request, "form.html", {"user": user, "error": None})


@router.post("/form", response_class=HTMLResponse)
def form_submit(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(get_optional_user),
    nik: str = Form(...),
    nama: str = Form(...),
    usia: int = Form(...),
    jenis_kelamin: str = Form(...),
    status_pernikahan: str = Form(...),
    jumlah_tanggungan: int = Form(...),
    alamat: str = Form(default=""),
    pendapatan: float = Form(...),
    status_pekerjaan: str = Form(default=""),
    aset_produktif: Optional[str] = Form(default=None),
    riwayat_bantuan: Optional[str] = Form(default=None),
    luas_rumah: Optional[float] = Form(default=None),
    jenis_lantai: str = Form(default=""),
    jenis_dinding: str = Form(default=""),
    sumber_air: str = Form(default=""),
    isi_teks: str = Form(default=""),
    sumber_teks: str = Form(default="petugas"),
):
    if not _require(user):
        return _redirect("/login")
    try:
        payload = PengajuanCreate(
            warga=WargaIn(
                nik=nik,
                nama=nama,
                usia=usia,
                jenis_kelamin=jenis_kelamin,
                status_pernikahan=status_pernikahan,
                jumlah_tanggungan=jumlah_tanggungan,
                alamat=alamat or None,
            ),
            data_survei=DataSurveiIn(
                pendapatan=pendapatan,
                status_pekerjaan=status_pekerjaan or None,
                aset_produktif=aset_produktif is not None,
                riwayat_bantuan=riwayat_bantuan is not None,
                luas_rumah=luas_rumah,
                jenis_lantai=jenis_lantai or None,
                jenis_dinding=jenis_dinding or None,
                sumber_air=sumber_air or None,
            ),
            teks_naratif=(
                [TeksNaratifIn(sumber=sumber_teks, isi_teks=isi_teks)] if isi_teks.strip() else []
            ),
        )
    except ValidationError as exc:
        return templates.TemplateResponse(
            request,
            "form.html",
            {"user": user, "error": str(exc)},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    pengajuan = create_pengajuan(db, user.id, payload)
    return _redirect(f"/detail/{pengajuan.id}")
