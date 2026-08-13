"""Tier 2 — klasifikasi kelayakan bansos (Random Forest vs Gradient Boosting, OI-01).

Submodul:
- `skema_fitur` : urutan fitur kanonik + perakitan vektor, dipakai bersama saat latih & inference
- `dataset`     : ekspor dari basis data + split latih/uji 80:20 stratified berkelompok per warga
- `train`       : perbandingan kandidat lewat validasi silang berulang, lalu ekspor artefak terbaik
- `evaluate`    : akurasi/presisi/recall/F1, confusion matrix, ROC-AUC, Brier, analisis FP/FN
- `infer`       : pemuatan artefak & prediksi (hasil, probabilitas, versi_model)

Batas klaim: metrik di atas data `sintetis` hanya memvalidasi pipa. Pemilihan model final dan
seluruh angka untuk skripsi diambil dari data `lokal` pada Fase 6 — lihat
`progres/evaluasi-pra-fase-3.md` §5.1.
"""

# Urutan fitur KANONIK. Disimpan ke metadata artefak dan diverifikasi saat inference;
# mengubah urutan/isi daftar ini membuat artefak lama tidak dapat dipakai (memang disengaja).
FITUR = [
    "pendapatan",
    "jumlah_tanggungan",
    "usia",
    "aset_produktif",
    "riwayat_bantuan",
    "housing_need",
    "skor_urgensi",
]

# Ablasi untuk data publik yang tidak punya teks naratif (mis. Alatas dkk. 2012), sehingga Tier 1
# tidak dapat menghasilkan `skor_urgensi`. Ini BUKAN varian yang boleh melayani pipeline live:
# `skema_fitur.periksa_skema()` sengaja menolak artefak berskema ini, karena aplikasi selalu
# merakit tujuh fitur dan model enam fitur akan menerima vektor yang bergeser tanpa galat.
# Gunanya murni pembandingan luring: memberi angka Tier 2 di atas data NYATA, menggantikan metrik
# sintetis yang sudah terbukti tidak dapat membedakan kandidat (evaluasi pra-Fase 3).
FITUR_TANPA_URGENSI = [f for f in FITUR if f != "skor_urgensi"]

# Nama himpunan fitur → daftarnya. Dipakai CLI, header CSV, dan metadata artefak agar ketiadaan
# fitur selalu punya nama yang sama di seluruh jalur.
SET_FITUR = {"lengkap": FITUR, "tanpa_urgensi": FITUR_TANPA_URGENSI}


def nama_set_fitur(fitur: list[str]) -> str:
    """Kebalikan `SET_FITUR`: kenali himpunan fitur, atau tolak yang tidak dikenal."""
    for nama, daftar in SET_FITUR.items():
        if list(fitur) == daftar:
            return nama
    raise ValueError(
        f"himpunan fitur tidak dikenal: {list(fitur)}. "
        f"Yang sah: { {k: v for k, v in SET_FITUR.items()} }"
    )

LABELS = ["tidak_layak", "layak"]
LABEL2ID = {label: i for i, label in enumerate(LABELS)}
ID2LABEL = {i: label for i, label in enumerate(LABELS)}

# Kelas positif = 'layak'. Presisi/recall selalu dilaporkan terhadap kelas ini.
KELAS_POSITIF = "layak"

VERSI_FALLBACK = "stub-logistik-fallback-v0"
NAMA_BERKAS_MODEL = "model.joblib"
