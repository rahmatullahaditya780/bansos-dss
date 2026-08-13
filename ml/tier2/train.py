"""Pelatihan & perbandingan Tier 2: Random Forest vs Gradient Boosting (OI-01).

**Pemilihan model dipisahkan dari pelaporan.** Pemenang ditentukan oleh *repeated stratified group
k-fold* di atas porsi latih (default 5 lipatan × 5 ulangan = 25 pengukuran per kandidat), sedangkan
holdout 80:20 tetap dievaluasi dan dilaporkan demi kepatuhan TRD. Alasannya di
`progres/evaluasi-pra-fase-3.md` §5.4: pada data lokal ≥100 KK, holdout hanya berisi ~20 baris —
selang kepercayaan akurasinya ±15 poin persen, terlalu lebar untuk memutuskan apa pun. Validasi
silang memakai setiap baris sebagai data uji secara bergiliran, sehingga jauh lebih stabil pada n kecil.

Lipatan tetap **dikelompokkan per warga** (`StratifiedGroupKFold`), sama seperti split latih/uji —
kalau tidak, kebocoran yang sudah dicegah di `dataset.py` akan masuk lagi lewat pintu belakang.

Aturan pemilihan (keputusan teknis #8 rencana Fase 3): peringkat berdasarkan **F1 kelas `layak`**;
bila selisih dua kandidat teratas lebih kecil daripada simpangan gabungannya, keduanya dinyatakan
**tidak dapat dibedakan** dan pemenang ditentukan oleh **recall kelas `layak`** yang lebih tinggi —
false negative berarti warga layak yang ditolak sistem, false positive masih akan tersaring
verifikasi manual petugas. Keputusan itu ikut ditulis ke metadata artefak, lengkap dengan alasannya.

Pemakaian:
    python -m ml.tier2.train --outdir ml/artifacts/tier2 --asal-data sintetis
"""
from __future__ import annotations

import argparse
import csv
import json
import platform
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ml.tier2 import KELAS_POSITIF, LABEL2ID, LABELS, NAMA_BERKAS_MODEL, nama_set_fitur
from ml.tier2.dataset import fitur_csv, muat_csv, ringkasan
from ml.tier2.evaluate import cetak_laporan, hitung_metrik
from ml.tier2.skema_fitur import matriks

ID_POSITIF = LABEL2ID[KELAS_POSITIF]
METRIK_CV = ["akurasi", "presisi", "recall", "f1", "roc_auc"]


@dataclass
class Kandidat:
    nama: str
    buat: Callable[[], object]
    seimbang: bool = False
    catatan: str = ""


def daftar_kandidat(seed: int) -> list[Kandidat]:
    """Grid kecil dan sengaja tidak diperluas — dua algoritma OI-01 + varian penyeimbang kelas."""
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier

    return [
        Kandidat(
            "random_forest",
            lambda: RandomForestClassifier(
                n_estimators=300, min_samples_leaf=2, random_state=seed, n_jobs=-1
            ),
        ),
        Kandidat(
            "random_forest_seimbang",
            lambda: RandomForestClassifier(
                n_estimators=300,
                min_samples_leaf=2,
                class_weight="balanced",
                random_state=seed,
                n_jobs=-1,
            ),
            seimbang=True,
            catatan="class_weight='balanced'",
        ),
        Kandidat(
            "gradient_boosting",
            lambda: GradientBoostingClassifier(random_state=seed),
        ),
        Kandidat(
            "gradient_boosting_seimbang",
            lambda: GradientBoostingClassifier(random_state=seed),
            seimbang=True,
            catatan="sample_weight='balanced' (GradientBoosting tidak punya class_weight)",
        ),
    ]


def _latih(model, X, y, seimbang: bool):
    """Fit dengan penyeimbangan kelas yang sesuai kemampuan estimator."""
    if seimbang and getattr(model, "class_weight", None) is None:
        from sklearn.utils.class_weight import compute_sample_weight

        model.fit(X, y, sample_weight=compute_sample_weight("balanced", y))
    else:
        model.fit(X, y)
    return model


def validasi_silang(
    kandidat: Kandidat, X, y, grup, *, lipatan: int, ulangan: int, seed: int
) -> dict[str, object]:
    """Jalankan repeated stratified group k-fold; kembalikan rerata ± simpangan tiap metrik."""
    import numpy as np
    from sklearn.model_selection import StratifiedGroupKFold

    kumpulan: dict[str, list[float]] = {m: [] for m in METRIK_CV}
    for u in range(ulangan):
        pembagi = StratifiedGroupKFold(n_splits=lipatan, shuffle=True, random_state=seed + u)
        for idx_latih, idx_uji in pembagi.split(X, y, grup):
            model = _latih(kandidat.buat(), X[idx_latih], y[idx_latih], kandidat.seimbang)
            prob = model.predict_proba(X[idx_uji])[:, ID_POSITIF]
            m = hitung_metrik(y[idx_uji], prob)
            for nama in METRIK_CV:
                if m[nama] is not None:
                    kumpulan[nama].append(float(m[nama]))

    hasil: dict[str, object] = {"nama": kandidat.nama, "catatan": kandidat.catatan,
                                "n_pengukuran": len(kumpulan["f1"])}
    for nama in METRIK_CV:
        nilai = kumpulan[nama]
        hasil[f"{nama}_rerata"] = round(float(np.mean(nilai)), 4) if nilai else None
        hasil[f"{nama}_simpangan"] = round(float(np.std(nilai, ddof=1)), 4) if len(nilai) > 1 else None
    return hasil


def pilih_pemenang(ringkas: list[dict]) -> tuple[str, str, bool]:
    """Kembalikan (nama pemenang, alasan, dapat_dibedakan) menurut aturan keputusan teknis #8."""
    urut = sorted(ringkas, key=lambda r: -(r["f1_rerata"] or 0.0))
    juara = urut[0]
    if len(urut) == 1:
        return juara["nama"], "kandidat tunggal", True

    penantang = urut[1]
    selisih = (juara["f1_rerata"] or 0.0) - (penantang["f1_rerata"] or 0.0)
    gabungan = (
        ((juara["f1_simpangan"] or 0.0) ** 2 + (penantang["f1_simpangan"] or 0.0) ** 2) ** 0.5
    )

    if selisih >= gabungan:
        return (
            juara["nama"],
            f"F1 kelas '{KELAS_POSITIF}' tertinggi; unggul {selisih:.4f} melampaui simpangan "
            f"gabungan {gabungan:.4f}",
            True,
        )

    setara = [r for r in urut if (juara["f1_rerata"] or 0.0) - (r["f1_rerata"] or 0.0) < gabungan]
    pilih = max(setara, key=lambda r: r["recall_rerata"] or 0.0)
    return (
        pilih["nama"],
        f"selisih F1 antar {len(setara)} kandidat teratas ({selisih:.4f}) lebih kecil daripada "
        f"simpangan gabungannya ({gabungan:.4f}) — TIDAK DAPAT DIBEDAKAN secara statistik. "
        f"Pemenang ditentukan oleh recall kelas '{KELAS_POSITIF}' tertinggi "
        f"({pilih['recall_rerata']:.4f}), sesuai keputusan teknis #8 rencana Fase 3.",
        False,
    )


def _tulis_perbandingan(ringkas: list[dict], path: Path) -> None:
    kolom = ["nama", "catatan", "n_pengukuran"] + [
        f"{m}_{s}" for m in METRIK_CV for s in ("rerata", "simpangan")
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=kolom)
        w.writeheader()
        for r in sorted(ringkas, key=lambda r: -(r["f1_rerata"] or 0.0)):
            w.writerow({k: r.get(k) for k in kolom})


def train(
    train_csv: str,
    test_csv: str,
    outdir: str,
    *,
    asal_data: str,
    versi_model: str | None = None,
    lipatan: int = 5,
    ulangan: int = 5,
    seed: int = 42,
) -> dict:
    import joblib
    import numpy as np
    import sklearn

    # Himpunan fitur diambil dari HEADER CSV, bukan dari `ml.tier2.FITUR`. Dengan begitu berkas
    # ablasi (6 fitur) dan berkas lengkap (7 fitur) tidak dapat tertukar, dan ketidakcocokan
    # antara berkas latih & uji ketahuan di sini — bukan menjadi vektor bergeser yang senyap.
    fitur = fitur_csv(train_csv)
    fitur_uji = fitur_csv(test_csv)
    if fitur != fitur_uji:
        raise SystemExit(
            f"Skema latih & uji berbeda.\n  latih: {fitur}\n  uji  : {fitur_uji}\n"
            "Ekspor ulang keduanya dengan mode yang sama."
        )
    set_fitur = nama_set_fitur(fitur)

    baris_latih = muat_csv(train_csv)
    baris_uji = muat_csv(test_csv)
    print(f"Skema: {set_fitur} ({len(fitur)} fitur)")
    print(f"Latih: {ringkasan(baris_latih)}")
    print(f"Uji  : {ringkasan(baris_uji)}")

    X = np.array(matriks([b.fitur for b in baris_latih], fitur))
    y = np.array([b.label_id for b in baris_latih])
    grup = np.array([b.warga_id for b in baris_latih])
    X_uji = np.array(matriks([b.fitur for b in baris_uji], fitur))
    y_uji = np.array([b.label_id for b in baris_uji])

    mulai = time.time()
    kandidat = daftar_kandidat(seed)
    print(
        f"\nValidasi silang {lipatan} lipatan × {ulangan} ulangan, dikelompokkan per warga "
        f"({len(set(grup.tolist()))} warga di porsi latih):"
    )
    ringkas = []
    for k in kandidat:
        r = validasi_silang(k, X, y, grup, lipatan=lipatan, ulangan=ulangan, seed=seed)
        ringkas.append(r)
        print(
            f"  {k.nama:28s} F1={r['f1_rerata']:.4f}±{r['f1_simpangan']:.4f}  "
            f"akurasi={r['akurasi_rerata']:.4f}±{r['akurasi_simpangan']:.4f}  "
            f"recall={r['recall_rerata']:.4f}"
        )

    nama_pemenang, alasan, dapat_dibedakan = pilih_pemenang(ringkas)
    print(f"\nPemenang: {nama_pemenang}\n  Alasan: {alasan}")

    # Latih ulang pemenang di SELURUH porsi latih, lalu ukur sekali di holdout.
    juara = next(k for k in kandidat if k.nama == nama_pemenang)
    model = _latih(juara.buat(), X, y, juara.seimbang)
    prob_uji = model.predict_proba(X_uji)[:, ID_POSITIF]
    metrik = hitung_metrik(y_uji, prob_uji)
    durasi = round(time.time() - mulai, 1)

    cetak_laporan(metrik, f"Holdout 80:20 — {nama_pemenang}")

    # Penanda ablasi masuk ke NAMA VERSI, bukan cuma ke metadata: penanda versi adalah satu-satunya
    # hal yang pernah menyingkap artefak salah-pakai di proyek ini (tiga kali), dan ia ikut
    # tercetak di UI serta tersimpan di baris basis data.
    sufiks = "" if set_fitur == "lengkap" else f"-{set_fitur.replace('_', '-')}"
    versi = versi_model or f"tier2-{nama_pemenang.replace('_', '-')}-{asal_data}{sufiks}-v1"
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out / NAMA_BERKAS_MODEL)

    cv_pemenang = next(r for r in ringkas if r["nama"] == nama_pemenang)
    metadata = {
        "versi_model": versi,
        "tier": 2,
        "tugas": "klasifikasi biner kelayakan (tidak_layak/layak)",
        "keluaran": "probabilitas kelas 'layak' (0..1) + label pada ambang 0,5",
        "asal_data": asal_data,
        "algoritma": nama_pemenang,
        "catatan_algoritma": juara.catatan,
        "fitur": fitur,
        "set_fitur": set_fitur,
        "dapat_melayani_pipeline": set_fitur == "lengkap",
        "catatan_skema": (
            None
            if set_fitur == "lengkap"
            else "Ablasi tanpa `skor_urgensi` — sumber datanya tidak punya teks naratif sehingga "
                 "Tier 1 tidak dapat memberi skor. Artefak ini SENGAJA ditolak `periksa_skema()` "
                 "dan hanya sah untuk pembandingan luring, bukan untuk melayani aplikasi."
        ),
        "kelas": LABELS,
        "hyperparameter": {
            k: v for k, v in model.get_params().items() if not k.startswith("_")
        },
        "pemilihan_model": {
            "prosedur": f"repeated stratified group k-fold ({lipatan}×{ulangan}), "
                        "dikelompokkan per warga",
            "kriteria": f"F1 kelas '{KELAS_POSITIF}'; penentu kedua = recall kelas "
                        f"'{KELAS_POSITIF}' (keputusan teknis #8)",
            "alasan": alasan,
            "dapat_dibedakan": dapat_dibedakan,
            "perbandingan": ringkas,
        },
        "data": {
            "train_csv": str(train_csv),
            "test_csv": str(test_csv),
            "latih": ringkasan(baris_latih),
            "uji": ringkasan(baris_uji),
            "split": "80:20 stratified, seluruh pengajuan satu warga tidak terpecah",
        },
        "durasi_latih_detik": durasi,
        "scikit_learn": sklearn.__version__,
        "python": platform.python_version(),
        "dilatih_pada": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (out / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    (out / "metrics.json").write_text(
        json.dumps(
            {
                "versi_model": versi,
                "asal_data": asal_data,
                "holdout": metrik,
                "validasi_silang": cv_pemenang,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    _tulis_perbandingan(ringkas, out / "perbandingan.csv")

    print(f"\nArtefak tersimpan di {out.resolve()}")
    if asal_data != "lokal":
        print(
            f"\n[BATAS KLAIM] asal data '{asal_data}'. Metrik di atas hanya memvalidasi pipa "
            "— bukan\n  kinerja pada data warga nyata. Angka untuk skripsi diambil dari versi "
            "'lokal' (Fase 6)."
        )
    if not dapat_dibedakan:
        print(
            "[PERINGATAN] Kandidat teratas TIDAK DAPAT DIBEDAKAN secara statistik. Jangan laporkan\n"
            "  pemenang ini sebagai temuan; ia hanya artefak pemilihan yang harus diulang di data lokal."
        )
    return {"metrik": metrik, "metadata": metadata, "perbandingan": ringkas}


def main() -> None:
    ap = argparse.ArgumentParser(description="Latih & bandingkan RF vs GB untuk Tier 2.")
    ap.add_argument("--train", default="data/corpus/tier2_train.csv")
    ap.add_argument("--test", default="data/corpus/tier2_test.csv")
    ap.add_argument("--outdir", default="ml/artifacts/tier2")
    ap.add_argument("--lipatan", type=int, default=5, help="jumlah lipatan k-fold")
    ap.add_argument("--ulangan", type=int, default=5, help="berapa kali k-fold diulang")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--asal-data", default="sintetis", help="sintetis | publik | lokal")
    ap.add_argument("--versi-model", default=None, help="default: tier2-<algoritma>-<asal>-v1")
    args = ap.parse_args()

    train(
        args.train,
        args.test,
        args.outdir,
        asal_data=args.asal_data,
        versi_model=args.versi_model,
        lipatan=args.lipatan,
        ulangan=args.ulangan,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
