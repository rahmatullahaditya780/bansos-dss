"""Uji silang: contoh terkalibrasi rubrik vs model Tier 1 yang sedang terpasang.

Ke-25 contoh di Bagian 6 rubrik ditulis manusia dengan gaya catatan petugas, sengaja menyimpang dari
pola bank klausa `ml/tier1/corpus.py`. Karena data uji augmentasi sudah jenuh (akurasi 1,0000 —
tidak ada lagi kasus salah yang bisa dipelajari), contoh-contoh inilah **uji jujur satu-satunya**
sampai teks lokal berlabel tersedia.

Yang diuji dua arah:
- apakah model sejalan dengan definisi rubrik (bila banyak meleset → korpus latih belum mewakili
  bahasa lapangan);
- apakah rubrik sejalan dengan asumsi data latih (bila meleset justru pada kasus yang rubriknya
  tegas → definisi perlu diselaraskan sebelum pelabelan sungguhan dimulai).

Jalankan:
    .venv/Scripts/python.exe progres/fase-1-data-pelabelan/uji_silang_rubrik.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))

from generate_rubrik_urgensi import CONTOH  # noqa: E402
from ml.tier1.infer import get_scorer  # noqa: E402

AMBANG = 0.5


def main() -> int:
    scorer = get_scorer(REPO / "ml" / "artifacts" / "indobert")
    info = scorer.info()
    if not info["tersedia"]:
        print(f"Artefak model tidak ditemukan di {info['model_path']} - latih dulu lewat ml.tier1.train.")
        return 1

    dinilai = [(no, teks, label, alasan) for no, teks, label, alasan in CONTOH
               if label in ("TINGGI", "RENDAH")]
    hasil = scorer.score_batch([teks for _, teks, _, _ in dinilai])

    print(f"Model    : {scorer.versi_model}")
    print(f"Contoh   : {len(dinilai)} dinilai, {len(CONTOH) - len(dinilai)} dilewati "
          f"(TIDAK DAPAT DINILAI)\n")
    print(f"{'#':>3}  {'rubrik':7} {'model':7} {'p(tinggi)':>9}  teks")
    print("-" * 100)

    meleset: list[tuple[str, str, str, float, str]] = []
    for (no, teks, label, alasan), h in zip(dinilai, hasil):
        prediksi = "TINGGI" if h.skor >= AMBANG else "RENDAH"
        tanda = " " if prediksi == label else "X"
        print(f"{no:>3}{tanda} {label:7} {prediksi:7} {h.skor:9.4f}  {teks[:66]}")
        if prediksi != label:
            meleset.append((no, label, prediksi, h.skor, alasan))

    n = len(dinilai)
    benar = n - len(meleset)
    print("-" * 100)
    print(f"Sepakat dengan rubrik: {benar}/{n} ({benar / n:.1%})\n")

    if meleset:
        print("Ketidaksepakatan - periksa satu per satu:")
        for no, label, prediksi, skor, alasan in meleset:
            print(f"  #{no}: rubrik {label}, model {prediksi} (p={skor:.4f})")
            print(f"       dasar rubrik: {alasan}")
        print("\nTindak lanjut: bila kasusnya tegas menurut rubrik, tambahkan pola kalimat serupa ke")
        print("bank klausa ml/tier1/corpus.py lalu latih ulang; bila rubriknya yang ambigu, perjelas")
        print("definisi indikator dan catat sebagai amandemen di Bagian 10 rubrik.")
    else:
        print("Model sepakat dengan seluruh contoh rubrik.")
        print("Catatan: ini syarat perlu, bukan bukti kesiapan - 25 kalimat terlalu sedikit untuk")
        print("menyimpulkan apa pun tentang bahasa lapangan yang sesungguhnya.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
