"""Logika pembuatan pengajuan, dipakai bersama oleh endpoint API dan form web."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.schemas.pengajuan import PengajuanCreate


def create_pengajuan(db: Session, user_id: int, data: PengajuanCreate) -> models.Pengajuan:
    warga = db.execute(
        select(models.Warga).where(models.Warga.nik == data.warga.nik)
    ).scalar_one_or_none()
    if warga is None:
        warga = models.Warga(**data.warga.model_dump())
        db.add(warga)
        db.flush()
    else:
        for field, value in data.warga.model_dump().items():
            setattr(warga, field, value)

    pengajuan = models.Pengajuan(
        warga_id=warga.id, dibuat_oleh=user_id, status=models.StatusPengajuan.BARU
    )
    db.add(pengajuan)
    db.flush()

    db.add(
        models.DataSurvei(pengajuan_id=pengajuan.id, asal_data="lokal", **data.data_survei.model_dump())
    )
    for t in data.teks_naratif:
        db.add(models.TeksNaratif(pengajuan_id=pengajuan.id, **t.model_dump()))

    db.commit()
    db.refresh(pengajuan)
    return pengajuan
