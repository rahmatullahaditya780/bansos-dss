# Sumber data — Indonesian Lapor! Application Dataset

Referensi gaya teks nyata untuk **Tier 1**. **Bukan data latih.**

## Identitas

| | |
|---|---|
| Judul | Indonesian Lapor! Application Dataset |
| Kontributor | Syahroni Wahyu Iriananda (Universitas Widyagama Malang) |
| Repositori | Mendeley Data, `vzn5jdgn4t`, versi 2 |
| Tautan | <https://data.mendeley.com/datasets/vzn5jdgn4t/2> |
| Terbit | 23 Januari 2018 |
| Lisensi | MIT |
| Sumber asal | Portal LAPOR! (SP4N), diunduh kontributor dari data.go.id |
| Diunduh | 13 Agustus 2026 |

## Berkas

| Berkas | Bita | SHA-256 |
|---|---|---|
| `stream_diknas_selesai.csv` | 44.426 | `15561AA8C1F962A49353EBCCE6FE9E14004FF65715D89A8EDCF2461490D30EC8` |

Verifikasi ulang:

```powershell
Get-FileHash data\public\lapor_mendeley\stream_diknas_selesai.csv -Algorithm SHA256
```

## Isi (terverifikasi saat pengunduhan)

- **117 baris data**, 14 kolom, UTF-8.
- Kolom: `id`, `JudulLaporan`, `IsiLaporan`, `DisposisiInstansi`, `DisposisiInstansiID`,
  `Kategori`, `KategoriID`, `Status`, `Area`, `AreaID`, `TanggalLaporanMasuk`,
  `TanggalDisposisi`, `TanggalLaporanDitutup`, `TanggalLaporanAktivitasTerakhir`.
- Kolom teks yang relevan: **`IsiLaporan`** — panjang min 30 / median 129 / maks 255 karakter.
- Sebaran `Kategori`: Kartu Indonesia Pintar (KIP) 106, Bantuan Siswa Miskin (BSM) 3,
  Pendidikan 3, Kepegawaian 2, Dikdasmen 2, Kepesertaan Kartu & Non-Kartu 1.
- `Status` seragam `Selesai` (117/117) — dataset ini hanya memuat laporan yang sudah ditutup.
- Rentang tanggal laporan masuk: 2015.

## ⚠️ Peringatan PII

Meski dataset ini terbit publik, **`IsiLaporan` memuat pengenal pribadi asli** — antara lain
nomor KKS pelapor (contoh nyata dalam berkas: `no kks 3374011412051053`), nama sekolah, dan
nama orang. Konsekuensinya:

1. Berkas CSV-nya **tidak di-commit** (lihat aturan `data/public/**/*.csv` di `.gitignore`).
2. Setiap kutipan yang masuk skripsi **wajib disunting** — sensor digit nomor kartu dan nama.
3. Jangan pernah menyalin isinya ke lembar kerja pelabelan yang di-commit.

## Peran dalam proyek

Bukan sumber pelatihan — 117 baris terlalu sedikit, dan labelnya (`Kategori`) adalah kategori
instansi, bukan urgensi.

Kegunaannya dua:

1. **Pembanding gaya.** Korpus Tier 1 saat ini 100% `asal_data=augmentasi` dan berpola template
   ("berdasarkan hasil observasi petugas di lapangan, …"), terpisah sempurna antar kelas —
   penyebab akurasi 1,0000 di Fase 2 dan saturasi `skor_urgensi` yang ditemukan pra-Fase 4.
   Berkas ini menunjukkan seperti apa register nyatanya: singkatan (`tdk`, `sja`, `pnm`), tanpa
   spasi setelah titik, kapitalisasi acak, kalimat menggantung.
2. **Uji nyata kecil.** Setelah dilabeli dengan
   `progres/fase-1-data-pelabelan/rubrik-pelabelan-urgensi.md`, 117 kalimat ini dapat dipakai
   sebagai himpunan uji di luar distribusi — indikator jujur atas generalisasi Tier 1.

## Catatan

Hanya sektor pendidikan (`stream_diknas`). Dataset SP4N-LAPOR lain di portal pemerintah daerah
umumnya **rekapitulasi angka, bukan teks** — contoh Open Data Aceh Jaya berisi harfiah dua kolom
(`tahun_2022,tahun_2023`). Sejauh penelusuran 13 Agustus 2026, tidak ada korpus publik berbahasa
Indonesia berisi narasi kondisi rumah tangga yang **berlabel urgensi**.
