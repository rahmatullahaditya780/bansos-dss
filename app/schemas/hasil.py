"""Schema hasil analisis, ranking, verifikasi, dan ringkasan dashboard."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class PrediksiMLOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hasil: str
    probabilitas: float
    versi_model: str


class TopsisOut(BaseModel):
    nilai_preferensi: float
    peringkat: int
    batch_id: str


class HasilResponse(BaseModel):
    """Gabungan keluaran tiga tier untuk satu pengajuan (GET /hasil/{id})."""

    pengajuan_id: int
    skor_urgensi: Optional[float] = None  # 0..1 (probabilitas kelas 'tinggi')
    prediksi_ml: Optional[PrediksiMLOut] = None
    topsis: Optional[TopsisOut] = None
    alasan: Optional[str] = None
    durasi_ms: Optional[int] = None


class RankingItem(BaseModel):
    peringkat: int
    pengajuan_id: int
    warga_nama: str
    nilai_preferensi: float
    prediksi: str
    skor_urgensi: Optional[float] = None


class AnalisisResult(BaseModel):
    """Ringkas keluaran POST /analisis/{id}."""

    pengajuan_id: int
    skor_urgensi: Optional[float] = None
    prediksi_ml: Optional[PrediksiMLOut] = None
    alasan: Optional[str] = None
    durasi_ms: int


class RankingResult(BaseModel):
    batch_id: str
    jumlah_alternatif: int
    ranking: list[RankingItem]


class VerifikasiIn(BaseModel):
    hasil_manual: Literal["layak", "tidak_layak"]


class DashboardRingkasan(BaseModel):
    total_pengajuan: int
    baru: int
    dianalisis: int
    diverifikasi: int
    layak: int
    tidak_layak: int
    rata_durasi_ms: Optional[float] = None
    persen_le_5s: Optional[float] = None
    efektivitas_persen: Optional[float] = None
