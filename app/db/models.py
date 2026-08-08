"""Model SQLAlchemy — skema database sesuai TRD Bab 6.4.

Enum direpresentasikan sebagai kolom String + konstanta Python (bukan tipe enum native DB)
agar portable antara SQLite dan PostgreSQL. Validasi nilai dilakukan di lapisan Pydantic.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---- Konstanta nilai (dipakai schema & service) ----
class Role:
    PETUGAS = "petugas"
    PEMOHON = "pemohon"


class StatusPengajuan:
    BARU = "baru"
    DIANALISIS = "dianalisis"
    DIVERIFIKASI = "diverifikasi"


class HasilKelayakan:
    LAYAK = "layak"
    TIDAK_LAYAK = "tidak_layak"


class SumberNaratif:
    PETUGAS = "petugas"
    MASYARAKAT = "masyarakat"
    SURAT = "surat"


class LabelUrgensi:
    TINGGI = "tinggi"
    RENDAH = "rendah"


# ---- Tabel ----
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(16), nullable=False, default=Role.PETUGAS)
    nama = Column(String(128), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    pengajuan_dibuat = relationship("Pengajuan", back_populates="pembuat")


class Warga(Base):
    __tablename__ = "warga"

    id = Column(Integer, primary_key=True)
    nik = Column(String(32), unique=True, nullable=False, index=True)
    nama = Column(String(128), nullable=False)
    usia = Column(Integer, nullable=False)
    jenis_kelamin = Column(String(16), nullable=False)  # L / P
    status_pernikahan = Column(String(32), nullable=False)
    jumlah_tanggungan = Column(Integer, nullable=False, default=0)
    alamat = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    pengajuan = relationship("Pengajuan", back_populates="warga", cascade="all, delete-orphan")


class Pengajuan(Base):
    __tablename__ = "pengajuan"

    id = Column(Integer, primary_key=True)
    warga_id = Column(ForeignKey("warga.id"), nullable=False, index=True)
    dibuat_oleh = Column(ForeignKey("users.id"), nullable=False)
    tanggal = Column(DateTime(timezone=True), default=_now, nullable=False)
    status = Column(String(24), nullable=False, default=StatusPengajuan.BARU, index=True)

    warga = relationship("Warga", back_populates="pengajuan")
    pembuat = relationship("User", back_populates="pengajuan_dibuat")
    data_survei = relationship(
        "DataSurvei", back_populates="pengajuan", uselist=False, cascade="all, delete-orphan"
    )
    teks_naratif = relationship(
        "TeksNaratif", back_populates="pengajuan", cascade="all, delete-orphan"
    )
    prediksi_ml = relationship(
        "PrediksiML", back_populates="pengajuan", uselist=False, cascade="all, delete-orphan"
    )
    ranking = relationship(
        "RankingTopsis", back_populates="pengajuan", cascade="all, delete-orphan"
    )
    log_pengujian = relationship(
        "LogPengujian", back_populates="pengajuan", cascade="all, delete-orphan"
    )
    verifikasi = relationship(
        "VerifikasiManual", back_populates="pengajuan", cascade="all, delete-orphan"
    )


class DataSurvei(Base):
    __tablename__ = "data_survei"

    id = Column(Integer, primary_key=True)
    pengajuan_id = Column(ForeignKey("pengajuan.id"), nullable=False, unique=True, index=True)
    # Ekonomi (FR-06)
    pendapatan = Column(Float, nullable=False)  # rupiah per kapita per bulan
    status_pekerjaan = Column(String(64), nullable=True)
    aset_produktif = Column(Boolean, nullable=False, default=False)
    riwayat_bantuan = Column(Boolean, nullable=False, default=False)
    # Kondisi rumah (FR-07)
    luas_rumah = Column(Float, nullable=True)  # m2
    jenis_lantai = Column(String(32), nullable=True)
    jenis_dinding = Column(String(32), nullable=True)
    sumber_air = Column(String(32), nullable=True)
    # Label target historis — HANYA untuk data latih/simulasi (boleh null di produksi)
    label_historis = Column(Boolean, nullable=True)
    # Asal data untuk pelacakan validitas: 'lokal' | 'publik' | 'sintetis'
    asal_data = Column(String(16), nullable=False, default="sintetis")

    pengajuan = relationship("Pengajuan", back_populates="data_survei")


class TeksNaratif(Base):
    __tablename__ = "teks_naratif"

    id = Column(Integer, primary_key=True)
    pengajuan_id = Column(ForeignKey("pengajuan.id"), nullable=False, index=True)
    sumber = Column(String(24), nullable=False, default=SumberNaratif.PETUGAS)
    isi_teks = Column(Text, nullable=False)
    label_urgensi_manual = Column(String(16), nullable=True)  # tinggi/rendah (data latih)

    pengajuan = relationship("Pengajuan", back_populates="teks_naratif")
    skor_urgensi = relationship(
        "SkorUrgensi", back_populates="teks_naratif", uselist=False, cascade="all, delete-orphan"
    )


class SkorUrgensi(Base):
    """Keluaran Tier 1 (IndoBERT)."""

    __tablename__ = "skor_urgensi"

    id = Column(Integer, primary_key=True)
    teks_naratif_id = Column(ForeignKey("teks_naratif.id"), nullable=False, unique=True, index=True)
    skor = Column(Float, nullable=False)  # 0..1 (probabilitas kelas 'tinggi')
    versi_model = Column(String(64), nullable=False)
    waktu_inference = Column(DateTime(timezone=True), default=_now, nullable=False)

    teks_naratif = relationship("TeksNaratif", back_populates="skor_urgensi")


class PrediksiML(Base):
    """Keluaran Tier 2 (klasifikasi kelayakan)."""

    __tablename__ = "prediksi_ml"

    id = Column(Integer, primary_key=True)
    pengajuan_id = Column(ForeignKey("pengajuan.id"), nullable=False, unique=True, index=True)
    hasil = Column(String(16), nullable=False)  # layak / tidak_layak
    probabilitas = Column(Float, nullable=False)
    versi_model = Column(String(64), nullable=False)
    waktu_prediksi = Column(DateTime(timezone=True), default=_now, nullable=False)

    pengajuan = relationship("Pengajuan", back_populates="prediksi_ml")


class RankingTopsis(Base):
    """Keluaran Tier 3 (Fuzzy TOPSIS) per batch perangkingan."""

    __tablename__ = "ranking_topsis"

    id = Column(Integer, primary_key=True)
    batch_id = Column(String(64), nullable=False, index=True)
    pengajuan_id = Column(ForeignKey("pengajuan.id"), nullable=False, index=True)
    nilai_preferensi = Column(Float, nullable=False)
    peringkat = Column(Integer, nullable=False)
    bobot_snapshot = Column(JSON, nullable=True)
    # Fase 5: bahan penjelasan Tier 3 (OI-07). Sebelumnya `RankingEntry` menghitung keempatnya lalu
    # membuangnya sebelum menyimpan, sehingga petugas tidak pernah tahu MENGAPA sebuah pengajuan
    # berada di posisinya (evaluasi pra-Fase 5 §5.2).
    jarak_positif = Column(Float, nullable=True)
    jarak_negatif = Column(Float, nullable=True)
    seri_dengan = Column(Integer, nullable=True)
    keanggotaan = Column(JSON, nullable=True)  # label linguistik per kriteria saat dirangking

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    pengajuan = relationship("Pengajuan", back_populates="ranking")


class LogPengujian(Base):
    """Bahan pengukuran EFISIENSI per pengajuan (TRD Bab 9.2, FR-25).

    Sejak Fase 5 tabel ini murni catatan waktu. Penilaian manual petugas pindah ke
    `verifikasi_manual`: menumpangkannya di sini membuat pasangan (sistem, manual) bergantung
    pada baris log mana yang kebetulan terbaru — analisis ulang membuat pasangan memakai putusan
    sistem yang lama, dan verifikasi-sebelum-analisis hilang tanpa peringatan
    (evaluasi pra-Fase 5 §5.4).
    """

    __tablename__ = "log_pengujian"

    id = Column(Integer, primary_key=True)
    pengajuan_id = Column(ForeignKey("pengajuan.id"), nullable=False, index=True)
    waktu_mulai = Column(DateTime(timezone=True), nullable=False)
    waktu_selesai = Column(DateTime(timezone=True), nullable=True)
    durasi_ms = Column(Integer, nullable=True)  # total Tier 1 + Tier 2 (per pengajuan)
    durasi_tier1_ms = Column(Integer, nullable=True)
    durasi_tier2_ms = Column(Integer, nullable=True)
    # 'cold' bila artefak model masih harus dimuat saat permintaan ini datang, 'warm' bila sudah.
    # Tanpa penanda ini, satu permintaan 14 detik per restart proses tercampur ke metrik NFR-01
    # sebagai kegagalan padahal ia biaya pemuatan model (evaluasi pra-Fase 5 §5.3).
    jenis_muat = Column(String(8), nullable=True)
    hasil_sistem = Column(String(16), nullable=True)  # layak / tidak_layak

    pengajuan = relationship("Pengajuan", back_populates="log_pengujian")


class LogRanking(Base):
    """Durasi Tier 3 — dicatat PER BATCH, bukan per pengajuan (FR-25).

    Tier 3 merangking seluruh alternatif sekaligus; membagi durasinya ke tiap pengajuan akan
    mengarang angka per-pengajuan yang tidak pernah diukur (evaluasi pra-Fase 5 §5.3, D-03).
    """

    __tablename__ = "log_ranking"

    id = Column(Integer, primary_key=True)
    batch_id = Column(String(64), nullable=False, index=True)
    jumlah_alternatif = Column(Integer, nullable=False)
    durasi_ms = Column(Integer, nullable=False)
    versi_metode = Column(String(64), nullable=False)
    versi_konfigurasi = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)


class VerifikasiManual(Base):
    """Penilaian manual petugas atas satu pengajuan (FR-26) — bahan EFEKTIVITAS (Bab 9.3, OI-18).

    Putusan sistem di-SNAPSHOT saat verifikasi direkam, bukan dirujuk belakangan. Petugas menilai
    apa yang dilihatnya; bila pengajuan dianalisis ulang setelah itu, perbandingan harus tetap
    mengacu pada putusan yang benar-benar dinilai — bukan pada putusan terbaru yang tidak pernah
    ia lihat.
    """

    __tablename__ = "verifikasi_manual"

    id = Column(Integer, primary_key=True)
    pengajuan_id = Column(ForeignKey("pengajuan.id"), nullable=False, index=True)
    petugas_id = Column(ForeignKey("users.id"), nullable=True)
    hasil_manual = Column(String(16), nullable=False)  # layak / tidak_layak
    # Snapshot putusan sistem PADA SAAT dinilai:
    hasil_sistem = Column(String(16), nullable=True)
    probabilitas_sistem = Column(Float, nullable=True)
    versi_model = Column(String(64), nullable=True)
    peringkat_sistem = Column(Integer, nullable=True)
    catatan = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    pengajuan = relationship("Pengajuan", back_populates="verifikasi")
    petugas = relationship("User")
