# Hasil Tier 2 di data publik — label musyawarah warga

**Artefak:** `tier2-gradient-boosting-seimbang-publik-musy-tanpa-urgensi-v1`
**Dilatih pertama kali:** 14 Agustus 2026 · **Direproduksi & disimpan:** 5 September 2026

Folder ini ada karena satu kesalahan yang hampir merugikan skripsi: pelatihan 14 Agustus dijalankan
di direktori sementara, sehingga **artefak dan metriknya hilang** dan angkanya hanya tersisa di
pesan commit `b0280a5`. Angka yang masuk Bab IV tidak boleh hanya hidup di riwayat git.

Yang disimpan di sini hanya berkas kecil yang dapat dilacak git — `metrics.json`, `metadata.json`,
`perbandingan.csv`. Model binernya ada di `ml/artifacts/tier2-publik-musy/model.joblib`
(tidak di-commit; `ml/artifacts/*` diabaikan git) dan dapat dibangun ulang dengan resep di bawah.

## Angka

| | Validasi silang 5×5 | Holdout n=757 |
|---|---|---|
| **F1 kelas 'layak'** | **0,5750 ± 0,0250** | **0,6090** |
| Akurasi | 0,6985 ± 0,0189 | 0,7133 ± 0,0322 |
| Recall 'layak' | 0,6786 | 0,7412 |
| Presisi 'layak' | 0,4996 | 0,5168 |
| ROC-AUC | 0,7594 | 0,7825 |
| Brier | — | 0,1906 |

Confusion holdout: TN=371 · FP=158 · FN=59 · TP=169.
Data: 3.788 rumah tangga → 3.031 latih / 757 uji, **kebocoran warga 0**.

**Pemenang dapat dibedakan secara statistik** — unggul 0,0572 melampaui simpangan gabungan 0,0385
(`dapat_dibedakan: true`). Ini pertama kalinya terjadi di proyek ini; pada data sintetis Fase 3
selisih kandidat 0,0005 vs simpangan 0,0201, dan pada label `poor` yang bocor keempat kandidat
sama-sama ±0,94.

## Cara membangun ulang (terverifikasi 5 September 2026 — hasilnya identik angka demi angka)

Prasyarat: arsip Dataverse sudah diekstrak ke `data/public/alatas2012/` (lihat
[`SUMBER.md`](../../../data/public/alatas2012/SUMBER.md)).

```bash
cd d:/Apps/Gilang/bansos-dss

# Basis data TERPISAH — jangan seed data publik ke bansos_dss.db yang dipakai demo
export DATABASE_URL="sqlite:///./bansos_publik.db"
export PYTHONIOENCODING=utf-8     # WAJIB di Windows, lihat catatan di bawah

.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m data.alatas.seed                 # 3.788 baris, asal_data='publik-musy'
.venv/Scripts/python.exe -m ml.tier2.dataset \
    --outdir data/corpus/publik-musy --asal-data publik-musy --tanpa-urgensi
.venv/Scripts/python.exe -m ml.tier2.train \
    --train data/corpus/publik-musy/tier2_train.csv \
    --test  data/corpus/publik-musy/tier2_test.csv \
    --outdir ml/artifacts/tier2-publik-musy --asal-data publik-musy
```

**`PYTHONIOENCODING=utf-8` bukan saran, melainkan syarat.** Tanpa itu `data.alatas.seed` mati di
konsol Windows sebelum menyentuh basis data — `UnicodeEncodeError` pada tanda `→` di baris ringkasan
yang dicetaknya, karena konsol bawaan memakai cp1252. Terbukti 5 September 2026 saat resep ini
dijalankan ulang untuk pertama kalinya di luar pytest.

## Batas pemakaian angka ini

- **Artefak 6 fitur (ablasi).** Sumbernya tanpa teks naratif, jadi `skor_urgensi` tidak ada.
  `periksa_skema()` **sengaja menolak** artefak ini melayani aplikasi — aplikasi selalu merakit
  tujuh fitur, dan model enam fitur akan menerima vektor bergeser satu posisi tanpa galat apa pun.
  Gunakan hanya untuk pembandingan luring.
- **Bukan angka final skripsi.** Konteks perdesaan/perkotaan tiga provinsi (survei 2008) ≠
  Bontoramba. Ini *proof-of-concept*; klaim final menunggu data lokal.
- **Jangan pernah melaporkan varian label `poor`** (F1 0,9431): labelnya adalah ambang deterministik
  atas `CONSUMPTION`, yang juga mengisi fitur `pendapatan`. Rinciannya di
  [`SUMBER.md` §Jebakan keenam](../../../data/public/alatas2012/SUMBER.md).
- Baca berdampingan dengan fakta bahwa **musyawarah warga sendiri hanya sepakat 66,3%** dengan
  kemiskinan berbasis konsumsi — "kebenaran" yang ditiru model memang penilaian manusia (OI-18).
