"""Probe pra-Fase 5 — apakah tujuan Fase 5 dapat dicapai dengan yang sekarang berdiri?

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

from app.db import models  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
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
        lab_expl = {
            "pendapatan": explanation.kategori_pendapatan(f["pendapatan"]),
            "housing_need": explanation.kategori_rumah(f["housing_need"]),
            "skor_urgensi": explanation.kategori_urgensi(urg),
        }
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

    print("Catatan: label fuzzy untuk skor_urgensi dihitung pada SKALA LOGIT (config Fase 4),")
    print("sedangkan explanation.kategori_urgensi() memotong probabilitas di 0,5.")

    # ------------------------------------------------ 2. daya beda penjelasan
    judul("2. Daya beda kalimat penjelasan (OI-07)")
    alasan = []
    for p, urg, f in baris:
        pred = p.prediksi_ml
        alasan.append(explanation.build_reason(f, urg, pred.hasil, pred.probabilitas))
    uniq = len(set(alasan))
    print(f"kalimat alasan dibuat    : {len(alasan)}")
    print(f"kalimat berbeda          : {uniq} ({persen(uniq, len(alasan))})")

    # Bagian yang benar-benar membedakan: frasa tanpa angka probabilitas.
    pola = [a.split(". Model memprediksi")[0] for a in alasan]
    print(f"pola frasa berbeda       : {len(set(pola))} (setelah membuang angka probabilitas)")
    urg_frasa = Counter(a.split("narasi menunjukkan urgensi ")[1].split(";")[0].split(".")[0]
                        for a in alasan if "narasi menunjukkan urgensi " in a)
    print(f"nilai frasa urgensi      : {dict(urg_frasa)}")
    print("\ncontoh 3 kalimat:")
    for a in alasan[:3]:
        print(f"    - {a}")

    print("\nYang TIDAK muncul di kalimat mana pun:")
    for kata, label in (
        ("peringkat", "posisi Tier 3 / nilai preferensi"),
        ("versi", "versi model yang memutuskan"),
        ("tanggungan tinggi", "kontribusi relatif tiap kriteria"),
    ):
        ada = sum(1 for a in alasan if kata in a.lower())
        print(f"    - {label:<38} muncul di {ada}/{len(alasan)} kalimat")

    # --------------------------------------------- 3. cakupan instrumen waktu
    judul("3. Cakupan instrumen waktu (FR-25) — bagian mana yang tercatat")
    logs = db.execute(select(models.LogPengujian)).scalars().all()
    durasi = sorted(log.durasi_ms for log in logs if log.durasi_ms is not None)
    if durasi:
        p50 = durasi[len(durasi) // 2]
        p90 = durasi[int(len(durasi) * 0.9)]
        print(f"baris log_pengujian      : {len(logs)}")
        print(f"durasi tercatat          : n={len(durasi)} min={durasi[0]} p50={p50} "
              f"p90={p90} max={durasi[-1]} (ms)")
        print(f"permintaan <= 5 detik    : {metrics.persen_di_bawah_ambang(durasi)}%")
        print(f"efisiensi (Bab 9.2) p50  : {metrics.hitung_efisiensi(p50)}%  "
              f"| max: {metrics.hitung_efisiensi(durasi[-1])}%")
        luar = [d for d in durasi if d > 5000]
        print(f"melanggar 5 detik        : {len(luar)} -> {luar}")

        # Apakah pelanggaran itu cold start (pemuatan artefak IndoBERT) atau beban sungguhan?
        urut = sorted(logs, key=lambda log: log.waktu_mulai)
        awal = [log.durasi_ms for log in urut[:5]]
        print(f"5 log paling awal (ms)   : {awal}  <- pemuatan artefak masuk hitungan")
        sisa = [log.durasi_ms for log in urut[1:] if log.durasi_ms is not None]
        if sisa:
            sisa_urut = sorted(sisa)
            print(f"tanpa permintaan pertama : n={len(sisa)} p50={sisa_urut[len(sisa_urut)//2]} "
                  f"max={sisa_urut[-1]} ms, <=5s {metrics.persen_di_bawah_ambang(sisa)}%")

    # Tier 3 tidak pernah masuk log — ukur berapa lama ia sebenarnya.
    layak = [(p, urg, f) for p, urg, f in baris if p.prediksi_ml.hasil == models.HasilKelayakan.LAYAK]
    alternatif = [
        {"pengajuan_id": p.id, **{k: f[k] for k in cfg["bobot"]}} for p, _u, f in layak
    ]
    t0 = time.perf_counter()
    hasil_rank = rank_topsis(alternatif, cfg["bobot"], cfg["arah"])
    t_rank = (time.perf_counter() - t0) * 1000
    print(f"\nTier 3 rank_topsis()     : {len(hasil_rank)} alternatif dalam {t_rank:.0f} ms "
          f"— TIDAK tercatat di log_pengujian mana pun")
    print("Artinya angka efisiensi yang dilaporkan hari ini hanya mencakup Tier 1 + Tier 2.")

    # ------------------------------------------- 4. kesiapan metrik efektivitas
    judul("4. Kesiapan efektivitas (OI-18, target >=85%)")
    dgn_sistem = sum(1 for log in logs if log.hasil_sistem)
    dgn_manual = sum(1 for log in logs if log.hasil_manual_petugas)
    pasang = sum(1 for log in logs if log.hasil_sistem and log.hasil_manual_petugas)
    print(f"log dengan hasil_sistem  : {dgn_sistem}")
    print(f"log dengan hasil_manual  : {dgn_manual}")
    print(f"pasangan lengkap         : {pasang}")
    print(f"efektivitas terhitung    : {dashboard_service.ringkasan(db).efektivitas_persen}")

    ganda = db.execute(
        select(models.LogPengujian.pengajuan_id, func.count())
        .group_by(models.LogPengujian.pengajuan_id)
        .having(func.count() > 1)
    ).all()
    print(f"pengajuan berlog ganda   : {len(ganda)} (analisis ulang membuat baris log BARU)")

    print("\nSimulasi urutan kerja petugas yang wajar (tanpa menyentuh basis data):")
    print("  a) analisis -> log#1 (sistem=layak)")
    print("  b) verifikasi manual -> log#1 (manual=tidak_layak)   [pasangan terbentuk]")
    print("  c) analisis ulang    -> log#2 (sistem=tidak_layak, manual=None)")
    simulasi = [("layak", "tidak_layak"), ("tidak_layak", None)]
    print(f"  efektivitas dihitung dari pasangan: {metrics.hitung_efektivitas(simulasi)}% "
          "-> memakai putusan sistem LAMA, bukan yang sekarang tampil di layar")
    print("\nUrutan sebaliknya (verifikasi dulu, analisis kemudian):")
    print("  a) verifikasi -> log#1 (manual=layak, sistem=None)")
    print("  b) analisis   -> log#2 (sistem=layak, manual=None)")
    print(f"  efektivitas: {metrics.hitung_efektivitas([('', 'layak'), ('layak', None)])} "
          "-> pasangan tidak pernah terbentuk, verifikasi hilang tanpa peringatan")

    # ---------------------------------------------------- 5. biaya instrumen
    judul("5. Biaya instrumen: ringkasan() dipanggil tiap 5 detik oleh dashboard")
    t0 = time.perf_counter()
    for _ in range(5):
        dashboard_service.ringkasan(db)
    t_ring = (time.perf_counter() - t0) / 5 * 1000
    print(f"ringkasan() rata-rata    : {t_ring:.1f} ms pada {len(logs)} baris log")
    print("Bentuk kuerinya memuat SELURUH baris log_pengujian ke memori tiap panggilan "
          "(select tanpa agregasi).")
    print(f"Perkiraan pada 10.000 baris: ~{t_ring * 10000 / max(len(logs), 1):.0f} ms per polling, "
          "dua kali per 10 detik per petugas yang membuka dashboard.")

    # ------------------------------------- 6. biaya halaman daftar (NFR-03)
    judul("6. Biaya halaman /daftar — dirender tanpa penyaring & tanpa paginasi")
    from app.templating import templates  # noqa: E402 (impor lokal: butuh filter Jinja terdaftar)

    t0 = time.perf_counter()
    rows = db.execute(
        select(models.Pengajuan).order_by(models.Pengajuan.tanggal.desc())
    ).scalars().all()
    t_query = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    html = templates.get_template("daftar.html").render(
        user=None, rows=rows, request=None
    )
    t_render = (time.perf_counter() - t0) * 1000
    print(f"baris dirender           : {len(rows)}")
    print(f"kueri                    : {t_query:.0f} ms (memuat seluruh tabel)")
    print(f"render Jinja             : {t_render:.0f} ms")
    print(f"ukuran HTML              : {len(html) / 1024:.0f} KiB")
    print("Belum ada paginasi, penyaring status, maupun pencarian NIK/nama pada rute /daftar.")

    # ------------------------------------------------------------- ringkasan
    judul("RINGKASAN")
    print(f"- Skew label penjelasan vs fuzzy : pendapatan {persen(beda['pendapatan'], n)}, "
          f"rumah {persen(beda['housing_need'], n)}, urgensi {persen(beda['skor_urgensi'], n)}")
    print(f"- Kalimat alasan berbeda         : {uniq}/{len(alasan)}")
    print(f"- Tier 3 di luar instrumen waktu : {t_rank:.0f} ms tidak tercatat")
    print(f"- Pasangan efektivitas tersedia  : {pasang} -> metrik tidak dapat dilaporkan")
    print(f"- ringkasan() per polling        : {t_ring:.1f} ms, O(n) terhadap baris log")
    print(f"- /daftar                        : {len(rows)} baris, {len(html) / 1024:.0f} KiB, "
          f"{t_query + t_render:.0f} ms tanpa paginasi")

    db.close()


if __name__ == "__main__":
    main()
