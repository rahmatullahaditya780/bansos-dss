"""Schema pengajuan, data survei, dan teks naratif (input & output)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

JenisKelamin = Literal["L", "P"]
SumberNaratif = Literal["petugas", "masyarakat", "surat"]
LabelUrgensi = Literal["tinggi", "rendah"]


# ---- Input ----
class WargaIn(BaseModel):
    nik: str = Field(min_length=8, max_length=32)
    nama: str = Field(min_length=1)
    usia: int = Field(ge=0, le=130)
    jenis_kelamin: JenisKelamin
    status_pernikahan: str
    jumlah_tanggungan: int = Field(ge=0)
    alamat: Optional[str] = None


class DataSurveiIn(BaseModel):
    pendapatan: float = Field(ge=0, description="Rupiah per kapita per bulan")
    status_pekerjaan: Optional[str] = None
    aset_produktif: bool = False
    riwayat_bantuan: bool = False
    luas_rumah: Optional[float] = Field(default=None, ge=0)
    jenis_lantai: Optional[str] = None
    jenis_dinding: Optional[str] = None
    sumber_air: Optional[str] = None


class TeksNaratifIn(BaseModel):
    sumber: SumberNaratif = "petugas"
    isi_teks: str = Field(min_length=1)
    label_urgensi_manual: Optional[LabelUrgensi] = None


class PengajuanCreate(BaseModel):
    warga: WargaIn
    data_survei: DataSurveiIn
    teks_naratif: list[TeksNaratifIn] = Field(default_factory=list)


class PengajuanUpdate(BaseModel):
    data_survei: Optional[DataSurveiIn] = None


# ---- Output ----
class WargaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nik: str
    nama: str
    usia: int
    jenis_kelamin: str
    status_pernikahan: str
    jumlah_tanggungan: int
    alamat: Optional[str] = None


class DataSurveiOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pendapatan: float
    status_pekerjaan: Optional[str] = None
    aset_produktif: bool
    riwayat_bantuan: bool
    luas_rumah: Optional[float] = None
    jenis_lantai: Optional[str] = None
    jenis_dinding: Optional[str] = None
    sumber_air: Optional[str] = None


class TeksNaratifOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sumber: str
    isi_teks: str
    label_urgensi_manual: Optional[str] = None


class PengajuanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    tanggal: datetime
    warga: WargaOut
    data_survei: Optional[DataSurveiOut] = None
    teks_naratif: list[TeksNaratifOut] = Field(default_factory=list)
