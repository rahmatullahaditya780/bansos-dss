"""Perhitungan efisiensi & efektivitas (TRD Bab 9.2/9.3, OI-18/OI-19).

Tiga hal yang diputuskan di Fase 5 dan tercermin di sini:

**D-02 — cold start dipisahkan.** Permintaan pertama setelah proses dimulai menanggung pemuatan
artefak IndoBERT: 13.998 ms, sementara permintaan berikutnya 209 ms (evaluasi pra-Fase 5 §5.3).
Mencampurnya membuat satu-satunya "pelanggaran NFR-01" di seluruh basis data sebenarnya adalah
biaya pemuatan model. Baris `cold` tetap dilaporkan — tidak disembunyikan — tetapi terpisah.

**Rumus Bab 9.2 dipakai sungguhan.** `hitung_efisiensi()` sebelumnya tidak dipanggil dari mana pun;
dashboard hanya menampilkan persentase ≤5 detik. Sekarang keduanya dilaporkan, karena masing-masing
menyembunyikan hal yang berbeda: rumusnya jenuh di 100% untuk hampir semua permintaan (p50 196 ms
→ 100,0%), sehingga rata-ratanya nyaris tanpa daya beda dan **distribusi wajib ikut dilaporkan**.

**Metrik menolak tampil pada masukan nol.** Efektivitas dari 0 pasangan bukan 0% dan bukan 100%;
ia `None`, dan jumlah pasangan selalu ikut dilaporkan agar pembaca tahu di atas berapa pengamatan
angka itu berdiri.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

WAKTU_IDEAL_DETIK = 5.0  # OI-19: batas atas dipakai sebagai nilai tunggal

__all__ = [
    "WAKTU_IDEAL_DETIK",
    "hitung_efisiensi",
    "persen_di_bawah_ambang",
    "hitung_efektivitas",
    "persentil",
    "RingkasanEfisiensi",
    "ringkas_efisiensi",
    "RingkasanEfektivitas",
    "ringkas_efektivitas",
]


def hitung_efisiensi(durasi_ms: float, waktu_ideal_detik: float = WAKTU_IDEAL_DETIK) -> float:
    """Efisiensi = min(waktu_ideal / waktu_aktual, 1) x 100% (di-cap 100%, OI-19)."""
    aktual = max(durasi_ms / 1000.0, 1e-6)
    return round(min(waktu_ideal_detik / aktual, 1.0) * 100.0, 2)


def persen_di_bawah_ambang(
    durations_ms: Sequence[Optional[int]], ambang_detik: float = WAKTU_IDEAL_DETIK
) -> Optional[float]:
    """Persentase permintaan dengan durasi <= ambang (metrik alternatif OI-19)."""
    valid = [d for d in durations_ms if d is not None]
    if not valid:
        return None
    n = sum(1 for d in valid if d / 1000.0 <= ambang_detik)
    return round(n / len(valid) * 100.0, 2)


def hitung_efektivitas(pairs: Sequence[tuple[Optional[str], Optional[str]]]) -> Optional[float]:
    """Efektivitas = (rekomendasi tepat / total pengujian) x 100%.

    pairs: daftar (hasil_sistem, hasil_manual_petugas). Baris tanpa keduanya diabaikan.
    Mengembalikan None bila tidak ada pasangan — bukan 0, yang akan terbaca sebagai
    "sistem selalu salah" padahal artinya "belum pernah diuji".
    """
    valid = [(s, m) for s, m in pairs if s and m]
    if not valid:
        return None
    tepat = sum(1 for s, m in valid if s == m)
    return round(tepat / len(valid) * 100.0, 2)


def persentil(nilai: Sequence[int], q: float) -> Optional[int]:
    """Persentil ke-q (0..1) dengan metode nearest-rank. None bila datanya kosong."""
    data = sorted(v for v in nilai if v is not None)
    if not data:
        return None
    idx = min(len(data) - 1, max(0, int(round(q * (len(data) - 1)))))
    return data[idx]


# --------------------------------------------------------------------------------------
# Efisiensi (Bab 9.2)
# --------------------------------------------------------------------------------------
@dataclass
class RingkasanEfisiensi:
    """Semua angka efisiensi yang layak dilaporkan, beserta ukuran populasinya.

    `n_cold` sengaja ikut: menyembunyikan permintaan cold sama menyesatkannya dengan
    mencampurnya ke rata-rata.
    """

    n: int = 0
    n_warm: int = 0
    n_cold: int = 0
    # Baris yang dicatat SEBELUM Fase 5 tidak punya penanda cold/warm. Ia tidak dianggap warm
    # (satu di antaranya justru cold start 13.998 ms) dan tidak dibuang diam-diam: dilaporkan
    # sebagai populasi tersendiri, supaya tidak ada angka yang berdiri di atas campuran dua rezim.
    n_tak_bertanda: int = 0
    p50_tak_bertanda_ms: Optional[int] = None
    maks_tak_bertanda_ms: Optional[int] = None
    efisiensi_persen: Optional[float] = None   # rerata rumus Bab 9.2 atas permintaan warm
    persen_le_5s: Optional[float] = None       # atas permintaan warm
    p50_ms: Optional[int] = None
    p90_ms: Optional[int] = None
    maks_ms: Optional[int] = None
    cold_maks_ms: Optional[int] = None
    tier1_p50_ms: Optional[int] = None
    tier2_p50_ms: Optional[int] = None
    # Tier 3 bersatuan PER BATCH, bukan per pengajuan (D-03) — jangan dijumlahkan ke atas.
    tier3_batch: int = 0
    tier3_p50_ms: Optional[int] = None
    tier3_maks_alternatif: Optional[int] = None

    @property
    def cukup_untuk_dilaporkan(self) -> bool:
        return self.n_warm > 0


def ringkas_efisiensi(
    baris: Sequence[tuple[Optional[int], Optional[int], Optional[int], Optional[str]]],
    batch_tier3: Sequence[tuple[Optional[int], Optional[int]]] = (),
) -> RingkasanEfisiensi:
    """Rakit ringkasan efisiensi.

    `baris`   : (durasi_ms, durasi_tier1_ms, durasi_tier2_ms, jenis_muat) per pengajuan.
    `batch_tier3`: (durasi_ms, jumlah_alternatif) per batch perangkingan.

    Baris tanpa `jenis_muat` (dicatat sebelum Fase 5) **tidak** dianggap warm. Menebak dari
    durasinya akan berarti mengarang penanda yang tidak pernah diukur; ia dilaporkan sebagai
    populasi tersendiri agar tidak ada angka yang berdiri di atas campuran dua rezim pengukuran.
    """
    total = [d for d, _t1, _t2, _j in baris if d is not None]
    warm = [d for d, _t1, _t2, j in baris if d is not None and j == "warm"]
    cold = [d for d, _t1, _t2, j in baris if d is not None and j == "cold"]
    tanpa = [d for d, _t1, _t2, j in baris if d is not None and j is None]
    t1 = [v for _d, v, _t2, j in baris if v is not None and j == "warm"]
    t2 = [v for _d, _t1, v, j in baris if v is not None and j == "warm"]
    t3 = [d for d, _n in batch_tier3 if d is not None]
    n_alt = [n for _d, n in batch_tier3 if n is not None]

    efisiensi = (
        round(sum(hitung_efisiensi(d) for d in warm) / len(warm), 2) if warm else None
    )
    return RingkasanEfisiensi(
        n=len(total),
        n_warm=len(warm),
        n_cold=len(cold),
        n_tak_bertanda=len(tanpa),
        p50_tak_bertanda_ms=persentil(tanpa, 0.5),
        maks_tak_bertanda_ms=max(tanpa) if tanpa else None,
        efisiensi_persen=efisiensi,
        persen_le_5s=persen_di_bawah_ambang(warm),
        p50_ms=persentil(warm, 0.5),
        p90_ms=persentil(warm, 0.9),
        maks_ms=max(warm) if warm else None,
        cold_maks_ms=max(cold) if cold else None,
        tier1_p50_ms=persentil(t1, 0.5),
        tier2_p50_ms=persentil(t2, 0.5),
        tier3_batch=len(t3),
        tier3_p50_ms=persentil(t3, 0.5),
        tier3_maks_alternatif=max(n_alt) if n_alt else None,
    )


# --------------------------------------------------------------------------------------
# Efektivitas (Bab 9.3, OI-18)
# --------------------------------------------------------------------------------------
@dataclass
class RingkasanEfektivitas:
    """Efektivitas beserta jumlah pengamatan yang menyusunnya.

    `persen` bernilai None selama belum ada pasangan; UI menampilkan "belum dapat dihitung",
    bukan 0%.
    """

    pasangan: int = 0
    tepat: int = 0
    persen: Optional[float] = None
    target_persen: float = 85.0
    salah_positif: int = 0  # sistem 'layak', petugas 'tidak_layak'
    salah_negatif: int = 0  # sistem 'tidak_layak', petugas 'layak'

    @property
    def memenuhi_target(self) -> Optional[bool]:
        return None if self.persen is None else self.persen >= self.target_persen


def ringkas_efektivitas(
    pairs: Sequence[tuple[Optional[str], Optional[str]]], target_persen: float = 85.0
) -> RingkasanEfektivitas:
    valid = [(s, m) for s, m in pairs if s and m]
    tepat = sum(1 for s, m in valid if s == m)
    return RingkasanEfektivitas(
        pasangan=len(valid),
        tepat=tepat,
        persen=hitung_efektivitas(valid),
        target_persen=target_persen,
        salah_positif=sum(1 for s, m in valid if s == "layak" and m == "tidak_layak"),
        salah_negatif=sum(1 for s, m in valid if s == "tidak_layak" and m == "layak"),
    )
