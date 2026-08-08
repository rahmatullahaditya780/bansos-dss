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
    seri_dengan: Optional[int] = None
    keanggotaan: Optional[dict[str, str]] = None
    versi_metode: Optional[str] = None
    versi_konfigurasi: Optional[str] = None


class PenjelasanOut(BaseModel):
    """Penjelasan terstruktur per tier (OI-07). `sumber_label` menandai dari mana label berasal —
    `keanggotaan-fuzzy-v1` berarti sepakat dengan fungsi keanggotaan yang dipakai merangking."""

    model_config = ConfigDict(from_attributes=True)

    label: dict[str, str] = {}
    sumber_label: str = ""
    tier1: str = ""
    tier2: str = ""
    tier3: Optional[str] = None
    kontribusi: list[dict] = []
    teks: str = ""


class HasilResponse(BaseModel):
    """Gabungan keluaran tiga tier untuk satu pengajuan (GET /hasil/{id})."""

    pengajuan_id: int
    skor_urgensi: Optional[float] = None  # 0..1 (probabilitas kelas 'tinggi')
    prediksi_ml: Optional[PrediksiMLOut] = None
    topsis: Optional[TopsisOut] = None
    alasan: Optional[str] = None
    penjelasan: Optional[PenjelasanOut] = None
    durasi_ms: Optional[int] = None
    durasi_tier1_ms: Optional[int] = None
    durasi_tier2_ms: Optional[int] = None
    jenis_muat: Optional[str] = None  # 'cold' | 'warm'


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
    # Ditandai agar batch yang dirangking TANPA logika fuzzy (konfigurasi keanggotaan tidak sah →
    # `topsis-crisp-fallback-v0`) tidak pernah tersangka keluaran Fuzzy TOPSIS.
    versi_metode: str = ""
    versi_konfigurasi: Optional[str] = None


class EfisiensiOut(BaseModel):
    """Metrik efisiensi (Bab 9.2). Semua angka dihitung atas permintaan `warm`."""

    model_config = ConfigDict(from_attributes=True)

    n: int = 0
    n_warm: int = 0
    n_cold: int = 0
    n_tak_bertanda: int = 0
    p50_tak_bertanda_ms: Optional[int] = None
    maks_tak_bertanda_ms: Optional[int] = None
    efisiensi_persen: Optional[float] = None
    persen_le_5s: Optional[float] = None
    p50_ms: Optional[int] = None
    p90_ms: Optional[int] = None
    maks_ms: Optional[int] = None
    cold_maks_ms: Optional[int] = None
    tier1_p50_ms: Optional[int] = None
    tier2_p50_ms: Optional[int] = None
    tier3_batch: int = 0
    tier3_p50_ms: Optional[int] = None
    tier3_maks_alternatif: Optional[int] = None


class EfektivitasOut(BaseModel):
    """Metrik efektivitas (Bab 9.3, OI-18). `persen` None = belum ada pasangan, bukan 0%."""

    model_config = ConfigDict(from_attributes=True)

    pasangan: int = 0
    tepat: int = 0
    persen: Optional[float] = None
    target_persen: float = 85.0
    salah_positif: int = 0
    salah_negatif: int = 0
    memenuhi_target: Optional[bool] = None


class StatusTierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nama: str
    versi: str
    fallback: bool
    keterangan: Optional[str] = None


class MetrikResponse(BaseModel):
    efisiensi: EfisiensiOut
    efektivitas: EfektivitasOut
    status_model: list[StatusTierOut] = []


class VerifikasiIn(BaseModel):
    hasil_manual: Literal["layak", "tidak_layak"]
    # Alasan petugas bila ia tidak sepakat dengan sistem — satu-satunya sumber untuk memahami
    # KENAPA efektivitas meleset, dan bahan analisis kesalahan di Fase 7.
    catatan: Optional[str] = None


class DashboardRingkasan(BaseModel):
    total_pengajuan: int
    baru: int
    dianalisis: int
    diverifikasi: int
    layak: int
    tidak_layak: int
    # Durasi & efisiensi dihitung atas permintaan `warm` saja; `permintaan_cold` melaporkan
    # berapa yang dikeluarkan beserta alasannya (biaya pemuatan artefak, bukan beban komputasi).
    rata_durasi_ms: Optional[float] = None
    p50_durasi_ms: Optional[int] = None
    persen_le_5s: Optional[float] = None
    efisiensi_persen: Optional[float] = None
    permintaan_cold: int = 0
    # `efektivitas_persen` None = belum dapat dihitung (0 pasangan), BUKAN 0%.
    efektivitas_persen: Optional[float] = None
    pasangan_verifikasi: int = 0
