"""Tier 3 — Perangkingan prioritas dengan Fuzzy TOPSIS (FR-18…FR-21).

Fase 4: stub TOPSIS crisp Fase 0 DIGANTI oleh Fuzzy TOPSIS penuh (`ml.tier3`). Kontrak
dipertahankan supaya `app/services/pipeline.py` tidak perlu berubah:

    rank_topsis(alternatives, bobot, arah) -> list[RankingEntry]

Bila konfigurasi fungsi keanggotaan (OI-13) tidak ada atau tidak sah, modul turun ke TOPSIS crisp
dan menandai hasilnya `topsis-crisp-fallback-v0` — pola yang sama dengan `heuristik-fallback-v0`
(Tier 1) dan `stub-logistik-fallback-v0` (Tier 2). Penandanya ikut tersimpan ke
`ranking_topsis.bobot_snapshot`, sehingga batch yang dirangking tanpa logika fuzzy tidak akan
pernah tercampur ke analisis.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from app.services.fuzzy_config import load_fuzzy_config
from ml.tier3 import VERSI_FALLBACK, VERSI_METODE
from ml.tier3.crisp import nilai_preferensi_crisp
from ml.tier3.fuzzy_topsis import rangking
from ml.tier3.keanggotaan import PUSTAKA_MF, KonfigurasiKeanggotaanError, muat_kriteria

logger = logging.getLogger(__name__)

__all__ = ["RankingEntry", "rank_topsis", "info_fuzzy"]

# Digit pembulatan SAAT MENYIMPAN/MENAMPILKAN saja. Pengurutan selalu memakai presisi penuh —
# membulatkan sebelum mengurutkan memproduksi seri yang tidak ada di datanya sendiri
# (evaluasi pra-Fase 4 §5.6).
DIGIT_TAMPILAN = 6


@dataclass
class RankingEntry:
    pengajuan_id: int
    nilai_preferensi: float
    peringkat: int
    # Kolom tambahan Fase 4; bernilai default agar pemanggil lama tetap berjalan.
    jarak_positif: float = 0.0
    jarak_negatif: float = 0.0
    seri_dengan: int = 0
    versi_metode: str = VERSI_METODE
    keanggotaan: dict[str, str] = field(default_factory=dict)


def _kriteria_fuzzy(bobot: Mapping[str, float]) -> tuple[dict, str | None]:
    """Muat definisi keanggotaan; kembalikan (kriteria, alasan_gagal)."""
    cfg = load_fuzzy_config()
    try:
        return muat_kriteria(cfg, list(bobot)), None
    except KonfigurasiKeanggotaanError as exc:
        return {}, str(exc)


def rank_topsis(
    alternatives: Sequence[Mapping[str, Any]],
    bobot: Mapping[str, float],
    arah: Mapping[str, str],
) -> list[RankingEntry]:
    """Rangking alternatif dengan Fuzzy TOPSIS.

    `alternatives`: daftar dict berisi 'pengajuan_id' + nilai tiap kriteria (kunci = kunci `bobot`).
    Kriteria berskala logit boleh menyertakan '<kriteria>_margin' — dipakai bila ada, karena lebih
    tepat daripada membalik probabilitas yang sudah kehilangan digit.
    """
    if not alternatives:
        return []

    cfg = load_fuzzy_config()
    kriteria, gagal = _kriteria_fuzzy(bobot)

    if gagal is not None:
        logger.warning(
            "Tier 3: konfigurasi keanggotaan tidak sah (%s). Memakai TOPSIS crisp cadangan '%s' — "
            "hasil BUKAN keluaran Fuzzy TOPSIS dan tidak sah untuk klaim evaluasi.",
            gagal, VERSI_FALLBACK,
        )
        return _rangking_crisp(alternatives, bobot, arah)

    hasil = rangking(
        alternatives,
        kriteria,
        bobot,
        arah,
        tiebreak=cfg.get("tiebreak") or [],
        mode="fuzzy",
    )
    peta = {int(a["pengajuan_id"]): a for a in alternatives}
    return [
        RankingEntry(
            pengajuan_id=h.pengajuan_id,
            nilai_preferensi=round(h.nilai_preferensi, DIGIT_TAMPILAN),
            peringkat=h.peringkat,
            jarak_positif=round(h.jarak_positif, DIGIT_TAMPILAN),
            jarak_negatif=round(h.jarak_negatif, DIGIT_TAMPILAN),
            seri_dengan=h.seri_dengan,
            versi_metode=VERSI_METODE,
            keanggotaan=_label_keanggotaan(kriteria, peta.get(h.pengajuan_id, {})),
        )
        for h in hasil
    ]


def _label_keanggotaan(kriteria: Mapping[str, Any], alt: Mapping[str, Any]) -> dict[str, str]:
    """Label linguistik per kriteria — untuk penjelasan ke petugas, bukan untuk menghitung."""
    label: dict[str, str] = {}
    for nama, kf in kriteria.items():
        nilai = float(alt.get(nama, 0.0) or 0.0)
        label[nama] = kf.label(nilai, alt.get(f"{nama}_margin"))
    return label


def _rangking_crisp(
    alternatives: Sequence[Mapping[str, Any]],
    bobot: Mapping[str, float],
    arah: Mapping[str, str],
) -> list[RankingEntry]:
    """Jalur cadangan: TOPSIS crisp, ditandai versi agar tak tersangka hasil fuzzy."""
    cc = nilai_preferensi_crisp(alternatives, bobot, arah)
    baris = sorted(
        zip(alternatives, cc), key=lambda p: (-p[1], int(p[0]["pengajuan_id"]))
    )
    return [
        RankingEntry(
            pengajuan_id=int(alt["pengajuan_id"]),
            nilai_preferensi=round(nilai, DIGIT_TAMPILAN),
            peringkat=i,
            versi_metode=VERSI_FALLBACK,
        )
        for i, (alt, nilai) in enumerate(baris, start=1)
    ]


def info_fuzzy() -> dict[str, object]:
    """Status Tier 3 — dipakai memverifikasi pemasangan konfigurasi, sejajar `info_model()`.

    Seperti `info()` Tier 2, pemuatan sengaja **dipaksa** lebih dulu: tanpa itu jawabannya selalu
    optimistis sebelum perangkingan pertama, persis kebalikan dari yang ingin diketahui orang yang
    memanggilnya untuk memastikan konfigurasi sudah benar.
    """
    cfg = load_fuzzy_config()
    kriteria, gagal = _kriteria_fuzzy(cfg.get("bobot") or {})
    return {
        "versi_konfigurasi": cfg.get("versi"),
        "versi_metode": VERSI_METODE if gagal is None else VERSI_FALLBACK,
        "pustaka_keanggotaan": PUSTAKA_MF,
        "kriteria": list(kriteria),
        "jumlah_himpunan": {k: len(v.himpunan) for k, v in kriteria.items()},
        "skala": {k: v.skala for k, v in kriteria.items()},
        "tiebreak": [b.get("kriteria") for b in (cfg.get("tiebreak") or [])],
        "fallback_aktif": gagal is not None,
        "alasan_fallback": gagal,
    }
