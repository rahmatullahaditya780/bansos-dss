"""Perhitungan untuk grafik dashboard — fungsi murni, tanpa basis data dan tanpa HTML.

Template hanya menerima angka yang siap digambar; ia tidak menghitung apa pun. Selain memudahkan
pengujian, pemisahan ini menjaga aturan lama proyek: **pembulatan hanya untuk tampilan**, tidak
pernah sebelum menghitung.

Bentuk grafik dipilih menurut pekerjaan datanya, dan hanya yang datanya benar-benar mendukung:

* sebaran nilai preferensi → histogram, karena yang ingin dilihat adalah **di mana garis kuota
  jatuh** — di daerah padat (beda peringkat 50 dan 51 nyaris seri) atau renggang (bedanya nyata);
* durasi terhadap anggaran 5 detik → **meter**, bukan histogram: pengamatan warm masih sedikit,
  dan histogram atas segelintir nilai berpura-pura menjadi distribusi;
* komposisi status → satu batang bertumpuk (bagian-terhadap-keseluruhan).

**Tren harian sengaja tidak ada di sini.** Pengajuan hanya tersebar di dua tanggal; grafik tren
atas dua titik bukan grafik. Ia menunggu data lokal (Fase 6/7).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

__all__ = ["Bin", "Sebaran", "histogram", "Potongan", "komposisi"]


@dataclass
class Bin:
    x0: float
    x1: float
    n: int
    tinggi_persen: float = 0.0   # relatif terhadap bin terpadat
    kiri_persen: float = 0.0     # posisi kiri dalam % lebar gambar
    lebar_persen: float = 0.0


@dataclass
class Sebaran:
    bins: list[Bin] = field(default_factory=list)
    n: int = 0
    minimum: Optional[float] = None
    maksimum: Optional[float] = None
    puncak: int = 0
    # Nilai pada garis potong kuota, dan posisinya dalam % lebar gambar.
    nilai_potong: Optional[float] = None
    potong_persen: Optional[float] = None
    kuota: Optional[int] = None

    @property
    def ada_isi(self) -> bool:
        return self.n > 0 and self.maksimum is not None and self.maksimum > self.minimum


def histogram(nilai: Sequence[float], bins: int = 20, kuota: Optional[int] = None) -> Sebaran:
    """Sebaran nilai + posisi garis potong kuota.

    `kuota` adalah banyaknya penerima yang muat; nilai potongnya = nilai preferensi peringkat
    ke-`kuota` saat diurutkan menurun. Garis itulah yang membuat grafiknya berguna: ia
    memperlihatkan apakah pemenang terakhir terpisah jelas dari yang pertama tidak lolos.
    """
    data = sorted(float(v) for v in nilai if v is not None)
    hasil = Sebaran(n=len(data))
    if not data:
        return hasil

    hasil.minimum, hasil.maksimum = data[0], data[-1]
    if hasil.maksimum <= hasil.minimum:  # semua nilai sama — tidak ada sebaran untuk digambar
        return hasil

    bins = max(4, bins)
    lebar = (hasil.maksimum - hasil.minimum) / bins
    cacah = [0] * bins
    for v in data:
        idx = int((v - hasil.minimum) / lebar)
        cacah[min(idx, bins - 1)] += 1
    hasil.puncak = max(cacah)

    for i, n in enumerate(cacah):
        hasil.bins.append(
            Bin(
                x0=hasil.minimum + i * lebar,
                x1=hasil.minimum + (i + 1) * lebar,
                n=n,
                tinggi_persen=(n / hasil.puncak * 100) if hasil.puncak else 0.0,
                kiri_persen=i / bins * 100,
                lebar_persen=100 / bins,
            )
        )

    if kuota and 0 < kuota <= len(data):
        hasil.kuota = kuota
        hasil.nilai_potong = data[-kuota]  # data menaik → ke-`kuota` dari atas
        rentang = hasil.maksimum - hasil.minimum
        hasil.potong_persen = (hasil.nilai_potong - hasil.minimum) / rentang * 100
    return hasil


@dataclass
class Potongan:
    label: str
    n: int
    persen: float
    langkah: int  # langkah ramp ordinal 1..4 (terang → gelap)


def komposisi(bagian: Sequence[tuple[str, int]]) -> list[Potongan]:
    """Bagian-terhadap-keseluruhan untuk satu batang bertumpuk.

    Bagian bernilai nol dibuang, bukan digambar setebal nol — segmen tak terlihat yang tetap
    muncul di legenda hanya menambah ingar tanpa menambah informasi.
    """
    total = sum(max(0, n) for _label, n in bagian)
    if total <= 0:
        return []
    keluar: list[Potongan] = []
    for i, (label, n) in enumerate(bagian):
        if n <= 0:
            continue
        keluar.append(
            Potongan(label=label, n=n, persen=n / total * 100, langkah=min(4, i + 1))
        )
    return keluar
