"""Endpoint pengajuan & input data (TRD Bab 8, FR-05..FR-10)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_petugas
from app.db import models
from app.db.session import get_db
from app.schemas.pengajuan import PengajuanCreate, PengajuanOut, PengajuanUpdate
from app.services.pengajuan_service import create_pengajuan

router = APIRouter(prefix="/pengajuan", tags=["pengajuan"])


def _get_or_404(db: Session, pengajuan_id: int) -> models.Pengajuan:
    p = db.get(models.Pengajuan, pengajuan_id)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pengajuan tidak ditemukan")
    return p


@router.post("", response_model=PengajuanOut, status_code=status.HTTP_201_CREATED)
def buat_pengajuan(
    payload: PengajuanCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_petugas),
) -> models.Pengajuan:
    return create_pengajuan(db, user.id, payload)


@router.get("", response_model=list[PengajuanOut])
def daftar_pengajuan(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_petugas),
) -> list[models.Pengajuan]:
    q = select(models.Pengajuan).order_by(models.Pengajuan.tanggal.desc())
    if status_filter:
        q = q.where(models.Pengajuan.status == status_filter)
    return list(db.execute(q).scalars().all())


@router.get("/{pengajuan_id}", response_model=PengajuanOut)
def detail_pengajuan(
    pengajuan_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> models.Pengajuan:
    p = _get_or_404(db, pengajuan_id)
    # RBAC (FR-04): pemohon tidak boleh mengakses data warga (belum ada keterkaitan akun-warga).
    if user.role != models.Role.PETUGAS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak")
    return p


@router.put("/{pengajuan_id}", response_model=PengajuanOut)
def perbarui_pengajuan(
    pengajuan_id: int,
    payload: PengajuanUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_petugas),
) -> models.Pengajuan:
    p = _get_or_404(db, pengajuan_id)
    if p.status != models.StatusPengajuan.BARU:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pengajuan sudah dianalisis; tidak dapat diubah",
        )
    if payload.data_survei is not None:
        data = payload.data_survei.model_dump()
        if p.data_survei is None:
            db.add(models.DataSurvei(pengajuan_id=p.id, asal_data="lokal", **data))
        else:
            for field, value in data.items():
                setattr(p.data_survei, field, value)
    db.commit()
    db.refresh(p)
    return p
