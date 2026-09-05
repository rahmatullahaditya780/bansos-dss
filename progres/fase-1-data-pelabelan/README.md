# Fase 1 — Data: Publik, Lokal & Pelabelan

**Jalur:** B (Data, non-koding) · **Target:** mulai minggu 1, berjalan terus · **Status:** 🔶 Berjalan

## Tujuan
Menyiapkan data untuk melatih pipeline (dataset publik) dan untuk klaim final (data lokal Bontoramba),
beserta prosedur pelabelan urgensi yang konsisten.

## Deliverable / Checklist
- [x] Unduh & siapkan **dataset publik** → **Alatas dkk. (2012)**, Harvard Dataverse, CC0, 5.756 RT ([`SUMBER.md`](../../data/public/alatas2012/SUMBER.md)) + korpus LAPOR! sebagai pembanding gaya. *Catatan: keduanya tabular/teks pendek — belum ada sumber publik untuk teks naratif Tier 1.*
- [x] **Harmonisasi skema** kolom publik → `data_survei` (`data/alatas/harmonisasi.py` + `seed.py`, 24 tes penjaga); hasil Tier 2 di [`hasil-publik-musy/`](hasil-publik-musy/)
- [ ] Urus **izin resmi** akses data DTKS/kependudukan kelurahan (OI-09) — **surat pertama ditolak sebagian (4 Sep 2026)**: data diri riwayat penerima dinilai sensitif. Permintaan disusun ulang tiga lapisan → [`permintaan-data-kelurahan-revisi.md`](permintaan-data-kelurahan-revisi.md). **Kini memblokir.**
- [x] Susun **rubrik pelabelan urgensi biner** (OI-11) → [`rubrik-pelabelan-urgensi.md`](rubrik-pelabelan-urgensi.md) / [PDF](rubrik-pelabelan-urgensi.pdf)
- [x] Susun **protokol validasi label historis** (OI-10) → [`protokol-validasi-label-historis.md`](protokol-validasi-label-historis.md) / [PDF](protokol-validasi-label-historis.pdf)
- [ ] Rekrut pelabel ke-2; jalankan Tahap 0 (kalibrasi) & Tahap 1 (pilot 50 teks); ukur Cohen's kappa (ambang ≥ 0,61)
- [ ] Terapkan pelabelan pada teks naratif **lokal** (sumber gold Tier 1)
- [ ] Target ukuran data (OI-08): ≥100 KK lokal untuk klaim final
- [ ] Jalankan sesi validasi label historis bersama petugas (OI-10)
- [ ] Ekspor CSV latih:uji = 80:20 tanpa kebocoran, dengan penanda asal data (publik/lokal) per baris

## Exit criteria
Tersedia dataset (publik untuk latih + lokal untuk final) dalam format CSV siap-pakai, rubrik pelabelan
terdokumentasi, dan skor kappa antar-pelabel terukur.

## Berkas di folder ini

| Berkas | Isi |
|---|---|
| `ketentuan-data-dtks-kelurahan.pdf` | Catatan persiapan permintaan data ke kelurahan (OI-09) — **disusun sebelum penolakan 4 Sep; lihat berkas berikut** |
| `permintaan-data-kelurahan-revisi.md` | **Evaluasi ulang permintaan data** setelah penolakan 4 Sep 2026 (tiga lapisan) |
| `hasil-publik-musy/` | Metrik & resep reproduksi Tier 2 di data publik, label musyawarah warga |
| `rubrik-pelabelan-urgensi.md` / `.pdf` | **Rubrik pelabelan urgensi** (OI-11) — panduan kerja pelabel |
| `protokol-validasi-label-historis.md` / `.pdf` | **Protokol validasi label historis** (OI-10) — panduan sesi bersama petugas |
| `lembar-kerja-kalibrasi-A/B.xlsx` | Lembar Tahap 0 berisi 25 kalimat kalibrasi (kuncinya di rubrik Bagian 6) |
| `generate_*.py` | Generator dokumen (konten + tata letak); jalankan ulang setelah mengedit isi |
| `doc_render.py` | Blok konten + perender Markdown & PDF, dipakai bersama oleh generator |
| `buat_lembar_kerja.py` | Membuat lembar kerja Excel per pelabel (dropdown label + rujukan cepat) |
| `hitung_kappa.py` | Cohen's kappa antar pelabel + berkas daftar ketidaksepakatan siap-adjudikasi |
| `uji_silang_rubrik.py` | Menguji contoh terkalibrasi rubrik terhadap model Tier 1 terpasang |

Dokumen `.md` dan `.pdf` **dihasilkan** dari skrip — edit konten di berkas `generate_*.py`, lalu
jalankan ulang. Menyunting `.md` langsung akan tertimpa.

```powershell
python progres/fase-1-data-pelabelan/generate_rubrik_urgensi.py
python progres/fase-1-data-pelabelan/generate_protokol_label_historis.py
python progres/fase-1-data-pelabelan/uji_silang_rubrik.py
```

## Alur pelabelan

```powershell
# Tahap 0 - kalibrasi bersama (25 contoh; kuncinya di rubrik Bagian 6)
python progres/fase-1-data-pelabelan/buat_lembar_kerja.py --contoh --pelabel A B

# Tahap 1 - pilot: satu berkas per pelabel, dari teks yang SUDAH dianonimkan
python progres/fase-1-data-pelabelan/buat_lembar_kerja.py --input teks_anonim.csv --pelabel A B

# Tahap 2 - ukur kesepakatan; ambang lanjut kappa >= 0,61
python progres/fase-1-data-pelabelan/hitung_kappa.py --a lembar-kerja-pelabelan-A.xlsx --b lembar-kerja-pelabelan-B.xlsx
```

Tiap pelabel mengisi salinannya sendiri dan tidak melihat lembar pelabel lain — bila saling melihat,
kappa mengukur kesepakatan semu. `hitung_kappa.py` menuliskan `ketidaksepakatan.xlsx` berisi hanya
baris yang berbeda, lengkap dengan kolom `label_final` dan `alasan_putusan` untuk sesi adjudikasi
Tahap 4. Baris `tidak_dapat_dinilai` dikeluarkan dari perhitungan kappa (bukan kelas model) dan
dilaporkan terpisah.

> **Jangan commit lembar kerja yang sudah terisi narasi warga.** Berkas kalibrasi aman karena
> kalimatnya buatan; lembar berisi teks lokal termasuk data pribadi — lihat `.gitignore`.

## Catatan & artefak
Taruh di folder ini: tautan/berkas dataset publik, skrip harmonisasi skema, ringkasan statistik data,
surat/izin (jangan commit data pribadi warga — lihat `.gitignore`).
