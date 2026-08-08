"""Probe Fase 5 — dijalankan DUA KALI: sebelum implementasi, dan sesudahnya sebagai bukti.

Keluaran pra-implementasi diarsipkan di `hasil_probe.txt` (itulah dasar keenam keputusan D-01…D-06);
keluaran pasca-implementasi di `hasil_probe_setelah.txt`. Skrip ini selalu mengukur sistem yang
sedang terpasang, sehingga kedua berkas itu dapat dibandingkan langsung.

Fase 5 menjanjikan tiga hal: dashboard penuh, **penjelasan** keputusan (OI-07), dan **instrumen
pengukuran** efisiensi/efektivitas (TRD Bab 9.2/9.3). Dua yang terakhir adalah klaim angka, dan
proyek ini sudah tiga kali membuktikan bahwa klaim angka yang tidak diprobe lebih dulu berakhir
sebagai temuan negatif. Skrip ini mengukur — atas basis data nyata, bukan contoh — apa yang
sebenarnya dapat dihitung hari ini.

Yang diperiksa:

  1. SKEW PENJELASAN — `app/services/explanation.py` memakai ambang kerasnya sendiri, sementara
     Fase 4 sudah membangun `KriteriaFuzzy.label()` sebagai SATU SUMBER untuk fuzzifikasi dan
     label penjelasan. Berapa persen keduanya tidak sepakat?
  2. DAYA BEDA PENJELASAN — berapa banyak kalimat alasan yang benar-benar berbeda di 300 pengajuan
     yang sudah dianalisis? Penjelasan yang seragam tidak menjelaskan apa pun.
  3. CAKUPAN INSTRUMEN WAKTU (FR-25) — bagian pipeline mana yang durasinya benar-benar tercatat.
  4. KESIAPAN EFEKTIVITAS (OI-18) — berapa pasangan (sistem, manual) yang tersedia, dan apakah
     mekanisme pemasangannya tahan terhadap analisis ulang.
  5. BIAYA INSTRUMEN — berapa lama `ringkasan()` yang dipanggil setiap 5 detik oleh dashboard.

Jalankan:  python progres/fase-5-dashboard-pengujian/probe_dashboard_metrik.py
"""
from __future__ import annotations

import os
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from sqlalchemy import func, select  # noqa: E402

from app.api.routes.web import UKURAN_HALAMAN  # noqa: E402
from app.db import models  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app as app_fastapi  # noqa: E402
from app.services import dashboard_service, explanation, metrics, pipeline  # noqa: E402
from app.services.fuzzy_config import load_fuzzy_config  # noqa: E402
from app.services.tier3_topsis import info_fuzzy, rank_topsis  # noqa: E402
from ml.tier3.keanggotaan import muat_kriteria  # noqa: E402

BARIS = "-" * 88


def judul(teks: str) -> None:
    print("\n" + BARIS)
    print(teks)
    print(BARIS)


def persen(a: int, b: int) -> str:
    return "n/a" if not b else f"{100.0 * a / b:.1f}%"


def main() -> None:
    db = SessionLocal()
    cfg = load_fuzzy_config()
    kriteria = muat_kriteria(cfg, list(cfg["bobot"]))

    print("PROBE PRA-FASE 5 — dashboard, penjelasan & instrumen pengujian")
    print(f"Basis data : {ROOT / 'bansos_dss.db'}")
    print(f"Tier 3     : {info_fuzzy()['versi_metode']} / cfg {info_fuzzy()['versi_konfigurasi']}")

    # ---------------------------------------------------------------- populasi
    dianalisis = db.execute(
        select(models.Pengajuan)
        .join(models.PrediksiML)
        .order_by(models.Pengajuan.id)
    ).scalars().all()

    judul("0. Populasi yang dapat dipakai")
    total = db.execute(select(func.count()).select_from(models.Pengajuan)).scalar_one()
    print(f"pengajuan total          : {total}")
    print(f"sudah dianalisis (Tier 2): {len(dianalisis)}")
    versi_t1 = Counter(
        s.versi_model for s in db.execute(select(models.SkorUrgensi)).scalars().all()
    )
    versi_t2 = Counter(
        p.versi_model for p in db.execute(select(models.PrediksiML)).scalars().all()
    )
    print(f"versi Tier 1 pada baris  : {dict(versi_t1)}")
    print(f"versi Tier 2 pada baris  : {dict(versi_t2)}")

    # Rakit fitur + label sekali, dipakai beberapa bagian di bawah.
    baris = []
    for p in dianalisis:
        if p.data_survei is None:
            continue
        urg = pipeline._urgensi_pengajuan(p)
        f = pipeline._features_pengajuan(p, urg)
        baris.append((p, urg, f))

    # ------------------------------------------------- 1. skew penjelasan/fuzzy
    judul("1. Skew: label penjelasan (explanation.py) vs label fuzzy (Fase 4)")
    print("Fase 4 membangun KriteriaFuzzy.label() eksplisit sebagai 'satu sumber untuk fuzzifikasi")
    print("DAN label penjelasan' (README Fase 4). Pertanyaannya: apakah penjelasan memakainya?\n")

    # Bandingkan MAKNA, bukan ejaan: 'sangat rendah' dan 'sangat_rendah' adalah label yang sama.
    norm = lambda s: s.replace("_", " ").strip().lower()  # noqa: E731

    beda = Counter()
    pasangan = {"pendapatan": Counter(), "housing_need": Counter(), "skor_urgensi": Counter()}
    for _p, urg, f in baris:
        semua = explanation.labeli(f)
        lab_expl = {k: semua[k] for k in ("pendapatan", "housing_need", "skor_urgensi")}
        lab_fuzzy = {
            k: kriteria[k].label(f[k]) for k in ("pendapatan", "housing_need", "skor_urgensi")
        }
        for k in lab_expl:
            pasangan[k][(lab_expl[k], lab_fuzzy[k])] += 1
            if norm(lab_expl[k]) != norm(lab_fuzzy[k]):
                beda[k] += 1

    n = len(baris)
    for k in ("pendapatan", "housing_need", "skor_urgensi"):
        print(f"[{k}] tidak sepakat: {beda[k]}/{n} ({persen(beda[k], n)})")
        for (a, b), c in pasangan[k].most_common(6):
            tanda = "  " if norm(a) == norm(b) else "!="
            print(f"    {tanda} penjelasan={a:<14} fuzzy={b:<14} {c:>5}")
        print()

    print("Catatan: label fuzzy untuk skor_urgensi dihitung pada SKALA LOGIT (config Fase 4).")
    print("Sebelum Fase 5, penjelasan memotong PROBABILITAS di 0,5 — itulah sumber 58% skew.")

    # ------------------------------------------------ 2. daya beda penjelasan
    judul("2. Daya beda kalimat penjelasan (OI-07)")
    # Memakai jalur yang sama dengan halaman detail — bukan memanggil generator secara terpisah,
    # supaya yang diukur benar-benar kalimat yang dibaca petugas.
    alasan = [pipeline.susun_hasil(p)["alasan"] or "" for p, _urg, _f in baris]
    uniq = len(set(alasan))
    print(f"kalimat alasan dibuat    : {len(alasan)}")
    print(f"kalimat berbeda          : {uniq} ({persen(uniq, len(alasan))})")

    # Bagian yang benar-benar membedakan: frasa tanpa angka probabilitas.
    pola = [a.split(". Model memprediksi")[0] for a in alasan]
    print(f"pola frasa berbeda       : {len(set(pola))} (setelah membuang angka probabilitas)")
    urg_frasa = Counter(
        a.split("Narasi menunjukkan urgensi ")[1].split(" (skor")[0]
        for a in alasan if "Narasi menunjukkan urgensi " in a
    )
    print(f"nilai frasa urgensi      : {dict(urg_frasa)}")
    print("\ncontoh 3 kalimat:")
    for a in alasan[:3]:
        print(f"    - {a}")

    print("\nCakupan isi kalimat (sebelum Fase 5 ketiganya 0/300):")
    for kata, label in (
        ("peringkat prioritas", "posisi Tier 3 / nilai preferensi"),
        ("indobert", "versi model Tier 1 yang memutuskan"),
        ("tier2-", "versi model Tier 2 yang memutuskan"),
    ):
        ada = sum(1 for a in alasan if kata in a.lower())
        print(f"    - {label:<38} muncul di {ada}/{len(alasan)} kalimat")

    with_kontrib = sum(
        1 for p, _urg, _f in baris
        if (pipeline.susun_hasil(p)["penjelasan"] or None)
        and pipeline.susun_hasil(p)["penjelasan"].kontribusi
    )
    print(f"    - {'tabel kontribusi kriteria':<38} tersedia di {with_kontrib}/{len(baris)} hasil")

    # --------------------------------------------- 3. cakupan instrumen waktu
    judul("3. Cakupan instrumen waktu (FR-25) — bagian mana yang tercatat")
    eff = dashboard_service.efisiensi(db)
    print(f"populasi: warm={eff.n_warm} cold={eff.n_cold} tanpa penanda={eff.n_tak_bertanda}")
    print(f"warm     : p50={eff.p50_ms} p90={eff.p90_ms} maks={eff.maks_ms} ms | "
          f"efisiensi Bab 9.2 {eff.efisiensi_persen}% | <=5s {eff.persen_le_5s}%")
    print(f"cold     : terlama {eff.cold_maks_ms} ms (dipisahkan, tidak dibuang)")
    print(f"per tier : T1 p50={eff.tier1_p50_ms} ms · T2 p50={eff.tier2_p50_ms} ms · "
          f"T3 p50={eff.tier3_p50_ms} ms PER BATCH ({eff.tier3_batch} batch, "
          f"terbesar {eff.tier3_maks_alternatif} alternatif)")
    logs = db.execute(select(models.LogPengujian)).scalars().all()
    campuran = sorted(log.durasi_ms for log in logs if log.durasi_ms is not None)
    if campuran:
        print("Bandingkan dengan cara lama — SELURUH baris dicampur tanpa memisahkan cold start:")
        print(f"    campuran ({len(campuran)} baris): p50={campuran[len(campuran)//2]} "
              f"max={campuran[-1]} ms, <=5s {metrics.persen_di_bawah_ambang(campuran)}%")
        print("    Angka 'maks' di baris itu adalah biaya pemuatan artefak, bukan beban "
              "permintaan.")

    # Tier 3 kini tercatat per batch (D-03); ukur ulang untuk membandingkan dengan yang tersimpan.
    layak = [(p, urg, f) for p, urg, f in baris if p.prediksi_ml.hasil == models.HasilKelayakan.LAYAK]
    alternatif = [
        {"pengajuan_id": p.id, **{k: f[k] for k in cfg["bobot"]}} for p, _u, f in layak
    ]
    t0 = time.perf_counter()
    hasil_rank = rank_topsis(alternatif, cfg["bobot"], cfg["arah"])
    t_rank = (time.perf_counter() - t0) * 1000
    tersimpan = db.execute(select(models.LogRanking).order_by(models.LogRanking.id.desc())).scalars().first()
    print(f"\nTier 3 rank_topsis()     : {len(hasil_rank)} alternatif dalam {t_rank:.0f} ms")
    if tersimpan:
        print(f"tercatat di log_ranking  : batch {tersimpan.batch_id}, "
              f"{tersimpan.jumlah_alternatif} alternatif, {tersimpan.durasi_ms} ms "
              f"({tersimpan.versi_metode})")
    else:
        print("tercatat di log_ranking  : BELUM ADA — jalankan perangkingan sekali")

    # ------------------------------------------- 4. kesiapan metrik efektivitas
    judul("4. Kesiapan efektivitas (OI-18, target >=85%)")
    from app.services import verifikasi as verifikasi_service  # noqa: E402

    dgn_sistem = sum(1 for log in logs if log.hasil_sistem)
    pasang_semua = verifikasi_service.pasangan_efektivitas(db)
    pasang = sum(1 for s, m in pasang_semua if s and m)
    efek = dashboard_service.efektivitas(db)
    print(f"log dengan hasil_sistem  : {dgn_sistem}")
    print(f"verifikasi manual terekam: {len(pasang_semua)}")
    print(f"pasangan lengkap         : {pasang}")
    print(f"efektivitas terhitung    : {efek.persen}  (None = belum dapat dihitung, BUKAN 0%)")

    ganda = db.execute(
        select(models.LogPengujian.pengajuan_id, func.count())
        .group_by(models.LogPengujian.pengajuan_id)
        .having(func.count() > 1)
    ).all()
    print(f"pengajuan berlog ganda   : {len(ganda)} (analisis ulang membuat baris log BARU)")

    print("\nDua urutan kerja yang SEBELUM Fase 5 merusak pasangan (kini ditutup, D-04):")
    print("  a) analisis -> verifikasi -> analisis ulang")
    print("     dulu: pasangan memakai putusan sistem LAMA tanpa tanda apa pun")
    print("     kini: putusan yang dinilai di-snapshot di `verifikasi_manual`, pasangan tetap sah")
    print("  b) verifikasi dulu -> analisis kemudian")
    print("     dulu: pasangan tak pernah terbentuk, verifikasi hilang tanpa peringatan")
    print("     kini: penilaian tersimpan, `hasil_sistem` NULL dan diabaikan metrik "
          "(bukan dihitung salah)")
    print(f"  salah positif / salah negatif saat ini: {efek.salah_positif} / {efek.salah_negatif}")

    # ---------------------------------------------------- 5. biaya instrumen
    judul("5. Biaya instrumen: ringkasan() dipanggil tiap 5 detik oleh dashboard")
    dashboard_service.ringkasan(db)  # panaskan: panggilan pertama menanggung pemuatan artefak
    t0 = time.perf_counter()
    for _ in range(20):
        dashboard_service.ringkasan(db)
    t_ring = (time.perf_counter() - t0) / 20 * 1000
    print(f"ringkasan() rata-rata    : {t_ring:.1f} ms pada {len(logs)} baris log")
    print("Pencacahan dikerjakan basis data; hanya kolom durasi yang diambil, bukan objek ORM.")
    print(f"Perkiraan pada 10.000 baris: ~{t_ring * 10000 / max(len(logs), 1):.0f} ms per polling "
          "(ekstrapolasi linear; bagian yang O(1) membuat angka sebenarnya lebih kecil).")

    # ------------------------------------- 6. biaya halaman daftar (NFR-03)
    judul("6. Biaya halaman sungguhan (lewat rute, bukan render template langsung)")
    from fastapi.testclient import TestClient  # noqa: E402

    total_pengajuan = db.execute(select(func.count()).select_from(models.Pengajuan)).scalar_one()
    klien = TestClient(app_fastapi)
    masuk = klien.post(
        "/login", data={"username": "petugas", "password": "petugas123"}, follow_redirects=False
    )
    if masuk.status_code not in (302, 303):
        print("tidak dapat login sebagai 'petugas' — lewati bagian ini")
    else:
        klien.get("/dashboard")  # buang permintaan pertama (pemuatan artefak)
        for jalur in ("/dashboard", "/daftar", "/daftar?q=a", "/peringkat", "/metrik"):
            t0 = time.perf_counter()
            resp = klien.get(jalur)
            ms = (time.perf_counter() - t0) * 1000
            print(f"    {jalur:<18} {resp.status_code}  {ms:6.0f} ms  "
                  f"{len(resp.content) / 1024:6.1f} KiB")
        print(f"\n/daftar merender {UKURAN_HALAMAN} dari {total_pengajuan} baris (berpaginasi, "
              "warga di-eager-load).")
        print("Sebelum Fase 5: seluruh 2.020 baris, 833 KiB, 1.801 ms, dengan pola N+1.")

    # ------------------------------------------------------------- ringkasan
    judul("RINGKASAN")
    print(f"- Skew label penjelasan vs fuzzy : pendapatan {persen(beda['pendapatan'], n)}, "
          f"rumah {persen(beda['housing_need'], n)}, urgensi {persen(beda['skor_urgensi'], n)}")
    print(f"- Kalimat alasan berbeda         : {uniq}/{len(alasan)}")
    print(f"- Tier 3 tercatat per batch      : "
          f"{tersimpan.durasi_ms if tersimpan else '-'} ms / "
          f"{tersimpan.jumlah_alternatif if tersimpan else '-'} alternatif")
    print(f"- Pasangan efektivitas tersedia  : {pasang}"
          f"{' -> metrik menolak tampil (benar)' if pasang == 0 else ''}")
    print(f"- ringkasan() per polling        : {t_ring:.1f} ms pada {len(logs)} baris log")
    print(f"- /daftar                        : {UKURAN_HALAMAN} baris per halaman dari "
          f"{total_pengajuan}, berpaginasi")

    db.close()


if __name__ == "__main__":
    main()
