"""Pemuatan korpus & pembagian latih:uji = 80:20 tanpa kebocoran.

Kebocoran (*leakage*) dicegah dengan mengelompokkan baris berdasarkan **teks hasil preprocess**:
teks identik (atau hanya beda tanda baca/singkatan) selalu jatuh ke sisi split yang sama, sehingga
tidak ada kalimat uji yang sudah pernah dilihat model saat latih.

Split bersifat *stratified* per label agar proporsi tinggi/rendah sama di kedua sisi, dan
deterministik terhadap `seed`.

Pemakaian:
    python -m ml.tier1.dataset --input data/corpus/tier1_urgensi.csv --outdir data/corpus
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import random
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from ml.tier1 import LABEL2ID
from ml.tier1.preprocessing import preprocess


@dataclass
class Baris:
    teks: str                 # teks mentah (sebagaimana diisi petugas)
    label: str                # 'tinggi' | 'rendah'
    asal_data: str = "augmentasi"
    kategori: str = ""
    gaya: str = ""
    teks_bersih: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not teks_bersih_valid(self.teks_bersih):
            self.teks_bersih = preprocess(self.teks)

    @property
    def label_id(self) -> int:
        return LABEL2ID[self.label]


def teks_bersih_valid(v: str) -> bool:
    return bool(v and v.strip())


def muat_csv(path: str | Path) -> list[Baris]:
    """Baca CSV korpus. Kolom wajib: `teks`, `label`. Kolom lain opsional."""
    path = Path(path)
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"Korpus kosong: {path}")
    wajib = {"teks", "label"}
    if not wajib.issubset(rows[0].keys()):
        raise ValueError(f"Kolom wajib {wajib} tidak lengkap di {path} (ada: {list(rows[0])})")

    baris: list[Baris] = []
    for r in rows:
        label = (r["label"] or "").strip().lower()
        if label not in LABEL2ID:
            raise ValueError(f"Label tidak dikenal: {label!r} (harus salah satu dari {list(LABEL2ID)})")
        teks = (r["teks"] or "").strip()
        if not teks:
            continue
        baris.append(
            Baris(
                teks=teks,
                label=label,
                asal_data=(r.get("asal_data") or "augmentasi").strip(),
                kategori=(r.get("kategori") or "").strip(),
                gaya=(r.get("gaya") or "").strip(),
            )
        )
    return baris


def _kunci_grup(b: Baris) -> str:
    """Kunci dedup: hash teks bersih tanpa tanda baca — menangkap duplikat semu."""
    inti = "".join(c for c in b.teks_bersih if c.isalnum() or c == " ")
    return hashlib.sha1(" ".join(inti.split()).encode("utf-8")).hexdigest()


def split_80_20(
    baris: list[Baris], test_size: float = 0.2, seed: int = 42
) -> tuple[list[Baris], list[Baris]]:
    """Bagi stratified per label, dengan grup teks-identik tidak terpecah antar split."""
    grup: dict[str, list[Baris]] = defaultdict(list)
    for b in baris:
        grup[_kunci_grup(b)].append(b)

    # Label grup = label mayoritas anggotanya (praktis selalu seragam pada korpus augmentasi).
    per_label: dict[str, list[list[Baris]]] = defaultdict(list)
    for anggota in grup.values():
        mayoritas = max(set(x.label for x in anggota), key=lambda l: sum(1 for x in anggota if x.label == l))
        per_label[mayoritas].append(anggota)

    rng = random.Random(seed)
    latih: list[Baris] = []
    uji: list[Baris] = []
    for label in sorted(per_label):
        grup_label = sorted(per_label[label], key=lambda g: _kunci_grup(g[0]))
        rng.shuffle(grup_label)
        n_uji = max(1, round(len(grup_label) * test_size))
        for g in grup_label[:n_uji]:
            uji.extend(g)
        for g in grup_label[n_uji:]:
            latih.extend(g)

    rng.shuffle(latih)
    rng.shuffle(uji)
    return latih, uji


def periksa_kebocoran(latih: list[Baris], uji: list[Baris]) -> int:
    """Kembalikan jumlah teks uji yang juga muncul di latih (harus 0)."""
    kunci_latih = {_kunci_grup(b) for b in latih}
    return sum(1 for b in uji if _kunci_grup(b) in kunci_latih)


def tulis_split(baris: list[Baris], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["teks", "teks_bersih", "label", "label_id", "kategori", "gaya", "asal_data"])
        for b in baris:
            w.writerow([b.teks, b.teks_bersih, b.label, b.label_id, b.kategori, b.gaya, b.asal_data])
    return path


def ringkasan(baris: list[Baris]) -> dict[str, object]:
    per_label: dict[str, int] = defaultdict(int)
    per_asal: dict[str, int] = defaultdict(int)
    for b in baris:
        per_label[b.label] += 1
        per_asal[b.asal_data] += 1
    panjang = [len(b.teks_bersih.split()) for b in baris] or [0]
    return {
        "jumlah": len(baris),
        "per_label": dict(per_label),
        "per_asal_data": dict(per_asal),
        "rata_kata": round(sum(panjang) / len(panjang), 1),
        "maks_kata": max(panjang),
    }


class TeksUrgensiDataset:
    """Dataset PyTorch: tokenisasi IndoBERT atas teks yang sudah di-preprocess."""

    def __init__(self, baris: list[Baris], tokenizer, max_length: int = 128) -> None:
        self.baris = baris
        # padding="longest": panjang mengikuti kalimat terpanjang di korpus, bukan `max_length`
        # penuh — hemat komputasi tanpa mengubah hasil (truncation tetap di `max_length`).
        self.enc = tokenizer(
            [b.teks_bersih for b in baris],
            truncation=True,
            padding="longest",
            max_length=max_length,
            return_tensors="pt",
        )
        import torch

        self.labels = torch.tensor([b.label_id for b in baris], dtype=torch.long)

    def __len__(self) -> int:
        return len(self.baris)

    def __getitem__(self, i: int) -> dict:
        item = {k: v[i] for k, v in self.enc.items()}
        item["labels"] = self.labels[i]
        return item


def main() -> None:
    ap = argparse.ArgumentParser(description="Bagi korpus Tier 1 menjadi latih:uji 80:20.")
    ap.add_argument("--input", default="data/corpus/tier1_urgensi.csv")
    ap.add_argument("--outdir", default="data/corpus")
    ap.add_argument("--test-size", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    baris = muat_csv(args.input)
    latih, uji = split_80_20(baris, test_size=args.test_size, seed=args.seed)
    bocor = periksa_kebocoran(latih, uji)

    outdir = Path(args.outdir)
    tulis_split(latih, outdir / "tier1_train.csv")
    tulis_split(uji, outdir / "tier1_test.csv")

    print(f"Total   : {ringkasan(baris)}")
    print(f"Latih   : {ringkasan(latih)}")
    print(f"Uji     : {ringkasan(uji)}")
    print(f"Kebocoran teks uji ke latih: {bocor} (harus 0)")
    print(f"Ditulis ke {outdir / 'tier1_train.csv'} & {outdir / 'tier1_test.csv'}")


if __name__ == "__main__":
    main()
