"""Fungsi keanggotaan & fuzzifikasi Tier 3 (FR-18, OI-13).

Satu sumber untuk fuzzifikasi *dan* penjelasan kategori ke petugas — meniru peran
`ml/tier2/skema_fitur.py` bagi Tier 2. Bila nanti dashboard menampilkan "pendapatan tergolong
sangat rendah", label itu harus berasal dari fungsi yang sama dengan yang dipakai menghitung
peringkat; kalau tidak, penjelasan dan keputusan bisa berbeda diam-diam.

**Fuzzifikasi memakai derajat keanggotaan penuh.** Nilai crisp tidak dipaksa masuk ke satu
himpunan linguistik; derajat keanggotaannya terhadap SELURUH himpunan dihitung, lalu bilangan
fuzzy hasil = rerata berbobot keanggotaan atas TFN wakil tiap himpunan. Varian "petakan ke satu
himpunan" — bentuk yang paling lazim ditulis di skripsi Fuzzy TOPSIS — sudah diuji dan ditolak:
ia memeras 991 alternatif menjadi 81 nilai preferensi dan menyeret **25 dari 50 kursi kuota ke
posisi seri** (evaluasi pra-Fase 4 §5.2). Varian ini justru sudah men-defuzzifikasi diam-diam di
langkah pertama; ia bukan lebih fuzzy, melainkan lebih kasar.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Sequence

from ml.tier3 import TFN

logger = logging.getLogger(__name__)

# scikit-fuzzy dipakai bila tersedia (TRD Bab 6: pustaka fuzzy = scikit-fuzzy). Ia ada di
# `requirements-ml.txt`, yang TIDAK terpasang pada instalasi `requirements.txt` polos — karena itu
# tersedia implementasi setara di dalam modul ini. Keduanya diuji berpadanan di `test_tier3.py`,
# supaya "cadangan" tidak berarti "diam-diam berbeda".
#
# scikit-fuzzy dipanggil **per kolom kriteria (vektor)**, bukan per nilai. Memanggilnya per skalar
# berarti mengalokasikan satu array numpy untuk satu angka; pada analisis sensitivitas (ratusan
# perangkingan atas ~1.000 alternatif) biaya itu mendominasi seluruh perhitungan. `trimf`/`trapmf`
# skalar di bawah adalah implementasi acuan murni-Python yang dipakai untuk penjelasan per-nilai.
try:  # pragma: no cover — cabang bergantung lingkungan
    from skfuzzy import membership as _skf

    PUSTAKA_MF = "scikit-fuzzy"
except ImportError:  # pragma: no cover
    _skf = None
    PUSTAKA_MF = "builtin-mf"


class KonfigurasiKeanggotaanError(ValueError):
    """Konfigurasi fungsi keanggotaan tidak sah — Tier 3 harus turun ke fallback bertanda."""


# --------------------------------------------------------------------------------------
# Fungsi keanggotaan dasar
# --------------------------------------------------------------------------------------
def trimf(x: float, titik: Sequence[float]) -> float:
    """Derajat keanggotaan segitiga; `titik` = [a, b, c] dengan a <= b <= c."""
    a, b, c = (float(t) for t in titik)
    if x <= a or x >= c:
        # Puncak berimpit dengan ujung (mis. [0, 0, 5]) — keanggotaan penuh tepat di ujung itu.
        return 1.0 if (x == b and (a == b or b == c)) else 0.0
    if x == b:
        return 1.0
    if x < b:
        return (x - a) / (b - a) if b > a else 1.0
    return (c - x) / (c - b) if c > b else 1.0


def trapmf(x: float, titik: Sequence[float]) -> float:
    """Derajat keanggotaan trapesium; `titik` = [a, b, c, d] dengan a <= b <= c <= d."""
    a, b, c, d = (float(t) for t in titik)
    if b <= x <= c:
        return 1.0
    if x <= a or x >= d:
        return 1.0 if (a == b and x == a) or (c == d and x == d) else 0.0
    if x < b:
        return (x - a) / (b - a) if b > a else 1.0
    return (d - x) / (d - c) if d > c else 1.0


_BENTUK = {"segitiga": (trimf, 3), "trapesium": (trapmf, 4)}


def derajat_kolom(nilai: Sequence[float], bentuk: str, titik: Sequence[float]) -> list[float]:
    """Derajat keanggotaan untuk SELURUH kolom sekaligus — jalur panas perangkingan.

    Memakai scikit-fuzzy secara vektor bila terpasang; bila tidak, memakai implementasi acuan
    murni-Python di atas. `test_tier3.py` menguji keduanya berpadanan agar jalur cadangan tidak
    diam-diam menghasilkan angka lain.
    """
    fn, _ = _BENTUK[bentuk]
    if _skf is None:
        return [fn(float(x), titik) for x in nilai]

    import numpy as np  # pragma: no cover — hanya bila scikit-fuzzy terpasang

    skf_fn = _skf.trimf if bentuk == "segitiga" else _skf.trapmf
    x = np.asarray(list(nilai), dtype=float)
    t = np.asarray([float(v) for v in titik], dtype=float)
    return [float(v) for v in skf_fn(x, t)]


# --------------------------------------------------------------------------------------
# Definisi per kriteria
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class HimpunanLinguistik:
    nama: str
    bentuk: str
    titik: tuple[float, ...]

    def derajat(self, x: float) -> float:
        fn, _ = _BENTUK[self.bentuk]
        return fn(x, self.titik)


@dataclass(frozen=True)
class KriteriaFuzzy:
    """Fungsi keanggotaan satu kriteria beserta domain & skala nilai crisp-nya."""

    nama: str
    domain: tuple[float, float]
    himpunan: tuple[HimpunanLinguistik, ...]
    skala: str = "linier"  # 'linier' | 'logit'
    satuan: str = ""

    # -- transformasi & penjepitan ------------------------------------------
    def nilai_crisp(self, nilai: float, margin: float | None = None) -> float:
        """Nilai yang benar-benar difuzzifikasi, setelah transformasi skala & penjepitan domain.

        Untuk `skala: logit`, `nilai` adalah probabilitas dan `margin` (bila diberikan) dipakai
        langsung — memakai margin yang dihitung model lebih tepat daripada membalik probabilitas
        yang mungkin sudah kehilangan digit.
        """
        if self.skala == "logit":
            x = margin if margin is not None else _ke_logit(nilai)
        else:
            x = float(nilai)
        lo, hi = self.domain
        return min(max(x, lo), hi)

    # -- fuzzifikasi --------------------------------------------------------
    def derajat_keanggotaan(self, nilai: float, margin: float | None = None) -> dict[str, float]:
        """Derajat keanggotaan terhadap SELURUH himpunan — bahan penjelasan & fuzzifikasi."""
        x = self.nilai_crisp(nilai, margin)
        return {h.nama: h.derajat(x) for h in self.himpunan}

    def label(self, nilai: float, margin: float | None = None) -> str:
        """Himpunan dengan derajat tertinggi — HANYA untuk penjelasan ke petugas.

        Jangan pakai ini untuk menghitung: memilih satu himpunan adalah persis defuzzifikasi dini
        yang ditolak di §5.2 evaluasi pra-Fase 4.
        """
        derajat = self.derajat_keanggotaan(nilai, margin)
        return max(derajat, key=lambda k: (derajat[k], -self._urutan(k)))

    def _urutan(self, nama: str) -> int:
        return next(i for i, h in enumerate(self.himpunan) if h.nama == nama)

    def fuzzifikasi(self, nilai: float, margin: float | None = None) -> TFN:
        """Nilai crisp -> bilangan fuzzy segitiga pada skala preferensi 0..1."""
        return self.fuzzifikasi_kolom([nilai], [margin])[0]

    def fuzzifikasi_kolom(
        self, nilai: Sequence[float], margin: Sequence[float | None] | None = None
    ) -> list[TFN]:
        """Fuzzifikasi seluruh kolom kriteria sekaligus — jalur yang dipakai perangkingan.

        TFN wakil himpunan ke-j dari k himpunan berpusat di j/(k-1) dengan lebar satu langkah;
        hasil akhir = rerata berbobot derajat keanggotaan. Karena derajat berubah kontinu terhadap
        nilai, urutan antar-alternatif di dalam satu kategori tetap terjaga — sementara bilangan
        fuzzy melebar di daerah perbatasan antar-kategori, yang memang di situlah ketidakpastian
        kategorisasinya berada.

        Versi skalar `fuzzifikasi()` memanggil fungsi ini dengan satu elemen, sehingga hanya ada
        satu implementasi yang dapat menyimpang.
        """
        margin = list(margin) if margin is not None else [None] * len(nilai)
        xs = [self.nilai_crisp(v, m) for v, m in zip(nilai, margin)]

        # Satu panggilan vektor per himpunan, bukan per nilai.
        derajat = [derajat_kolom(xs, h.bentuk, h.titik) for h in self.himpunan]

        k = len(self.himpunan)
        lebar = 1.0 / (k - 1) if k > 1 else 1.0
        pusat = [j * lebar for j in range(k)]
        batas_bawah = [max(0.0, p - lebar) for p in pusat]
        batas_atas = [min(1.0, p + lebar) for p in pusat]

        hasil: list[TFN] = []
        for i, x in enumerate(xs):
            bobot_mu = [derajat[j][i] for j in range(k)]
            total = sum(bobot_mu)
            if total <= 1e-12:
                # Di luar dukungan seluruh himpunan (konfigurasi berlubang). Jatuhkan ke himpunan
                # terdekat agar sistem tetap merangking, dan beritahu — ini cacat konfigurasi.
                logger.warning(
                    "Tier 3: nilai %s pada kriteria '%s' tidak tercakup himpunan mana pun; "
                    "periksa 'domain' dan 'titik' di fuzzy_config.yaml",
                    x, self.nama,
                )
                j_dekat = min(range(k), key=lambda j: abs(x - _puncak(self.himpunan[j])))
                bobot_mu = [1.0 if j == j_dekat else 0.0 for j in range(k)]
                total = 1.0

            l = sum(w * batas_bawah[j] for j, w in enumerate(bobot_mu) if w)
            m = sum(w * pusat[j] for j, w in enumerate(bobot_mu) if w)
            u = sum(w * batas_atas[j] for j, w in enumerate(bobot_mu) if w)
            hasil.append((l / total, m / total, u / total))
        return hasil


def _puncak(h: HimpunanLinguistik) -> float:
    """Titik puncak himpunan (b untuk segitiga; tengah plateau untuk trapesium)."""
    t = h.titik
    return float(t[1]) if len(t) == 3 else (float(t[1]) + float(t[2])) / 2.0


def _ke_logit(p: float) -> float:
    import math

    eps = 1e-12
    p = min(max(float(p), eps), 1.0 - eps)
    return math.log(p / (1.0 - p))


# --------------------------------------------------------------------------------------
# Pemuatan dari konfigurasi
# --------------------------------------------------------------------------------------
def muat_kriteria(cfg: dict[str, Any], kriteria: Sequence[str]) -> dict[str, KriteriaFuzzy]:
    """Baca blok `keanggotaan` dan validasi ketat.

    Gagal berisik, bukan diam-diam: konfigurasi keanggotaan yang salah menghasilkan perangkingan
    yang tetap terlihat masuk akal padahal keliru, dan tidak ada label kebenaran yang akan
    menangkapnya (§5.5). Pemanggil menangkap galat ini lalu turun ke fallback bertanda versi.
    """
    blok = cfg.get("keanggotaan") or {}
    if not blok:
        raise KonfigurasiKeanggotaanError("blok 'keanggotaan' tidak ada di konfigurasi fuzzy")

    hasil: dict[str, KriteriaFuzzy] = {}
    for nama in kriteria:
        spec = blok.get(nama)
        if not spec:
            raise KonfigurasiKeanggotaanError(f"fungsi keanggotaan kriteria '{nama}' tidak ada")
        hasil[nama] = _baca_kriteria(nama, spec)
    return hasil


def _baca_kriteria(nama: str, spec: dict[str, Any]) -> KriteriaFuzzy:
    domain = spec.get("domain")
    if not (isinstance(domain, (list, tuple)) and len(domain) == 2 and domain[0] < domain[1]):
        raise KonfigurasiKeanggotaanError(f"'{nama}': domain harus [min, maks] dengan min < maks")

    daftar = spec.get("himpunan") or []
    if len(daftar) < 2:
        raise KonfigurasiKeanggotaanError(f"'{nama}': perlu minimal dua himpunan linguistik")

    himpunan: list[HimpunanLinguistik] = []
    for item in daftar:
        bentuk = item.get("bentuk")
        if bentuk not in _BENTUK:
            raise KonfigurasiKeanggotaanError(
                f"'{nama}': bentuk '{bentuk}' tidak dikenal (pilih: {', '.join(_BENTUK)})"
            )
        titik = [float(t) for t in (item.get("titik") or [])]
        _, jumlah = _BENTUK[bentuk]
        if len(titik) != jumlah:
            raise KonfigurasiKeanggotaanError(
                f"'{nama}' himpunan '{item.get('nama')}': {bentuk} butuh {jumlah} titik, "
                f"diberi {len(titik)}"
            )
        if any(titik[i] > titik[i + 1] for i in range(len(titik) - 1)):
            raise KonfigurasiKeanggotaanError(
                f"'{nama}' himpunan '{item.get('nama')}': titik harus menaik, diberi {titik}"
            )
        himpunan.append(
            HimpunanLinguistik(nama=str(item.get("nama")), bentuk=bentuk, titik=tuple(titik))
        )

    puncak = [_puncak(h) for h in himpunan]
    if any(puncak[i] > puncak[i + 1] for i in range(len(puncak) - 1)):
        raise KonfigurasiKeanggotaanError(
            f"'{nama}': himpunan harus diurutkan menaik menurut puncaknya, diberi {puncak}"
        )

    skala = spec.get("skala", "linier")
    if skala not in ("linier", "logit"):
        raise KonfigurasiKeanggotaanError(f"'{nama}': skala '{skala}' tidak dikenal")

    return KriteriaFuzzy(
        nama=nama,
        domain=(float(domain[0]), float(domain[1])),
        himpunan=tuple(himpunan),
        skala=skala,
        satuan=str(spec.get("satuan", "")),
    )
