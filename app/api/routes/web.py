"""Rute web (HTML) — dashboard server-rendered (Jinja2 + Bootstrap + HTMX).

Autentikasi berbasis cookie (di-set saat login). Halaman butuh peran petugas; bila belum
login, dialihkan ke /login.
"""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import COOKIE_NAME, authenticate_user, get_optional_user
from app.core.config import settings
from app.core.security import create_access_token
from app.db import models
from app.db.session import get_db
from app.schemas.pengajuan import DataSurveiIn, PengajuanCreate, TeksNaratifIn, WargaIn
from app.services import dashboard_service, pipeline
from app.services import verifikasi as verifikasi_service
from app.services.pengajuan_service import create_pengajuan
from app.templating import templates

router = APIRouter(tags=["web"], include_in_schema=False)


def _redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=status.HTTP_303_SEE_OTHER)


def _require(user: Optional[models.User]) -> bool:
    return user is not None and user.role == models.Role.PETUGAS


def _toast(resp, pesan: str, jenis: str = "good"):
    """Sisipkan kabar hasil tindakan ke tanggapan HTMX.

    Dikirim lewat header `HX-Trigger`; base.html yang merender pilnya. Jenis menentukan ikon DAN
    kata — warna tidak pernah berdiri sendiri.
    """
    resp.headers["HX-Trigger"] = json.dumps({"toast": {"pesan": pesan, "jenis": jenis}})
    return resp


def _ctx(user: Optional[models.User], **extra) -> dict:
    """Konteks template + status pemasangan model (D-05).

    `status_model` disuntikkan ke SETIAP halaman, bukan hanya halaman metrik: penanda versi yang
    hanya muncul di satu tempat tersembunyi persis sama tidak bergunanya dengan yang hanya ada di
    baris perintah. Biayanya 0,47 ms per halaman.
    """
    return {"user": user, "status_model": dashboard_service.status_model(), **extra}


# ---- Auth ----
@router.get("/", response_class=HTMLResponse)
def home(user: Optional[models.User] = Depends(get_optional_user)):
    return _redirect("/dashboard") if user else _redirect("/login")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: Optional[models.User] = Depends(get_optional_user)):
    if user:
        return _redirect("/dashboard")
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, username, password)
    if user is None:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Username atau password salah"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    token = create_access_token(user.id, user.role)
    resp = _redirect("/dashboard")
    resp.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return resp


@router.get("/logout")
def logout():
    resp = _redirect("/login")
    resp.delete_cookie(COOKIE_NAME)
    return resp


# ---- Dashboard ----
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(get_optional_user),
):
    if not _require(user):
        return _redirect("/login")
    recent = db.execute(
        select(models.Pengajuan)
        .options(joinedload(models.Pengajuan.warga))
        .order_by(models.Pengajuan.tanggal.desc())
        .limit(8)
    ).scalars().all()
    r = dashboard_service.ringkasan(db)
    # `tanda` ikut dirender sejak muat pertama supaya tarikan pertama (5 detik kemudian) sudah
    # dapat dijawab 204 bila tak ada yang berubah — tanpa ini selalu ada satu penukaran percuma.
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        _ctx(user, r=r, tanda=dashboard_service.tanda_ringkasan(r), recent=recent),
    )


@router.get("/dashboard/ringkasan-partial", response_class=HTMLResponse)
def dashboard_partial(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(get_optional_user),
    sig: str = "",
):
    """Blok ringkasan yang ditarik ulang dashboard tiap 5 detik.

    Bila angkanya tidak berubah, jawab **204 No Content** — HTMX tidak menukar apa pun. Tanpa ini
    seluruh blok diganti tiap 5 detik meski isinya sama persis: satu kedip berkala, dan grafik
    komposisi di dalamnya akan tumbuh ulang selamanya. `sig` dibawa oleh elemen yang sedang
    menarik (lihat `partials/_ringkasan.html`), sehingga tidak perlu keadaan di sisi server.
    """
    if not _require(user):
        return HTMLResponse("", status_code=status.HTTP_401_UNAUTHORIZED)
    r = dashboard_service.ringkasan(db)
    tanda = dashboard_service.tanda_ringkasan(r)
    if sig and sig == tanda:
        return HTMLResponse(status_code=status.HTTP_204_NO_CONTENT)
    return templates.TemplateResponse(
        request, "partials/_ringkasan.html", {"r": r, "tanda": tanda}
    )


@router.post("/dashboard/analisis-batch", response_class=HTMLResponse)
def dashboard_analisis_batch(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(get_optional_user),
    sudah: int = 0,
    gagal: int = 0,
    # 15 × ~200 ms ≈ 3 detik per gelombang. Terukur: 25 pengajuan memakan 4.949 ms — tepat di
    # garis 5 detik yang dipakai proyek ini menilai dirinya sendiri (NFR-01), jadi sengaja
    # diambil lebih kecil. Total waktu keseluruhan tidak berubah, hanya kabarnya lebih sering.
    limit: int = 15,
):
    """Satu gelombang analisis massal; pecahan yang dikembalikan memicu gelombang berikutnya.

    Menutup cacat yang paling terasa: dashboard menyebut ribuan pengajuan menunggu sementara
    petugas hanya bisa menganalisis satu per satu lewat halaman detail.
    """
    if not _require(user):
        return HTMLResponse("", status_code=status.HTTP_401_UNAUTHORIZED)

    hasil = pipeline.analisis_batch(db, limit=min(max(1, limit), 100))
    return templates.TemplateResponse(
        request,
        "partials/_batch_progres.html",
        {
            "total_diproses": sudah + hasil["diproses"],
            "total_gagal": gagal + hasil["gagal"],
            # Bila satu gelombang penuh gagal semua, hentikan rantainya daripada berputar selamanya.
            "sisa": hasil["sisa"] if hasil["diproses"] else 0,
        },
    )


# ---- Daftar pengajuan ----
UKURAN_HALAMAN = 25

# Pilihan pengurutan daftar. Kunci dipakai di URL (`?urut=`), sehingga pilihan petugas ikut
# tersalin saat tautan dibagikan.
URUTAN = {
    "terbaru": ("Terbaru", models.Pengajuan.tanggal.desc()),
    "terlama": ("Terlama", models.Pengajuan.tanggal.asc()),
    "nama": ("Nama A–Z", models.Warga.nama.asc()),
    "tanggungan": ("Tanggungan terbanyak", models.Warga.jumlah_tanggungan.desc()),
}


@router.get("/daftar", response_class=HTMLResponse)
def daftar(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(get_optional_user),
    q: str = "",
    status_filter: str = "",
    hasil: str = "",
    urut: str = "terbaru",
    halaman: int = 1,
):
    """Daftar pengajuan: paginasi, pencarian, penyaring status & kelayakan, pengurutan.

    Sampai Fase 4 rute ini merender SELURUH tabel (2.020 baris = 833 KiB, 1,8 detik, pola N+1)
    dan **tidak menampilkan hasil apa pun** — tanpa kolom kelayakan maupun peringkat, petugas
    harus membuka detail satu per satu untuk mengetahui apa pun. Keduanya ditutup di sini:
    `prediksi_ml` ikut dimuat lewat `joinedload`, dan peringkat batch terakhir diambil dalam
    satu kueri untuk baris yang tampil saja.
    """
    if not _require(user):
        return _redirect("/login")

    stmt = (
        select(models.Pengajuan)
        .join(models.Warga)
        .outerjoin(models.PrediksiML)
        .options(
            joinedload(models.Pengajuan.warga),
            joinedload(models.Pengajuan.prediksi_ml),
        )
    )
    if status_filter in (models.StatusPengajuan.BARU, models.StatusPengajuan.DIANALISIS,
                         models.StatusPengajuan.DIVERIFIKASI):
        stmt = stmt.where(models.Pengajuan.status == status_filter)
    if hasil in (models.HasilKelayakan.LAYAK, models.HasilKelayakan.TIDAK_LAYAK):
        stmt = stmt.where(models.PrediksiML.hasil == hasil)
    elif hasil == "belum":
        stmt = stmt.where(models.PrediksiML.id.is_(None))
    kata = q.strip()
    if kata:
        pola = f"%{kata}%"
        stmt = stmt.where(models.Warga.nama.ilike(pola) | models.Warga.nik.ilike(pola))

    total = db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()
    halaman = max(1, halaman)
    jumlah_halaman = max(1, -(-total // UKURAN_HALAMAN))
    halaman = min(halaman, jumlah_halaman)

    urut = urut if urut in URUTAN else "terbaru"
    rows = db.execute(
        stmt.order_by(URUTAN[urut][1])
        .offset((halaman - 1) * UKURAN_HALAMAN)
        .limit(UKURAN_HALAMAN)
    ).scalars().all()

    # Peringkat batch terakhir untuk baris yang TAMPIL saja — satu kueri tambahan, bukan satu
    # per baris; pola N+1 sudah pernah membuat halaman ini memakan 1,8 detik.
    peringkat: dict[int, int] = {}
    if rows:
        batch_id = db.execute(
            select(models.RankingTopsis.batch_id)
            .order_by(models.RankingTopsis.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if batch_id:
            peringkat = dict(
                db.execute(
                    select(models.RankingTopsis.pengajuan_id, models.RankingTopsis.peringkat)
                    .where(
                        models.RankingTopsis.batch_id == batch_id,
                        models.RankingTopsis.pengajuan_id.in_([p.id for p in rows]),
                    )
                ).all()
            )

    return templates.TemplateResponse(
        request,
        "daftar.html",
        _ctx(
            user,
            rows=rows,
            peringkat=peringkat,
            q=kata,
            status_filter=status_filter,
            hasil=hasil,
            urut=urut,
            urutan_pilihan={k: v[0] for k, v in URUTAN.items()},
            halaman=halaman,
            jumlah_halaman=jumlah_halaman,
            total=total,
        ),
    )


# ---- Detail + analisis (HTMX) ----
@router.get("/detail/{pengajuan_id}", response_class=HTMLResponse)
def detail(
    pengajuan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(get_optional_user),
):
    if not _require(user):
        return _redirect("/login")
    p = db.get(models.Pengajuan, pengajuan_id)
    if p is None:
        return HTMLResponse("Pengajuan tidak ditemukan", status_code=status.HTTP_404_NOT_FOUND)
    # Navigasi antar-pengajuan: memverifikasi 145 kandidat satu per satu lewat jalan memutar
    # daftar → detail → kembali → detail berikutnya adalah gesekan yang tidak perlu.
    sebelumnya = db.execute(
        select(models.Pengajuan.id).where(models.Pengajuan.id < p.id)
        .order_by(models.Pengajuan.id.desc()).limit(1)
    ).scalar_one_or_none()
    berikutnya = db.execute(
        select(models.Pengajuan.id).where(models.Pengajuan.id > p.id)
        .order_by(models.Pengajuan.id.asc()).limit(1)
    ).scalar_one_or_none()

    return templates.TemplateResponse(
        request,
        "detail.html",
        _ctx(
            user,
            p=p,
            hasil=pipeline.susun_hasil(p),
            verifikasi=verifikasi_service.verifikasi_terakhir(db, p.id),
            sebelumnya=sebelumnya,
            berikutnya=berikutnya,
        ),
    )


@router.post("/detail/{pengajuan_id}/verifikasi", response_class=HTMLResponse)
def detail_verifikasi(
    pengajuan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(get_optional_user),
    hasil_manual: str = Form(...),
    catatan: str = Form(default=""),
):
    """Rekam verifikasi manual dari antarmuka (FR-26).

    Sampai Fase 4 perekaman ini hanya ada sebagai endpoint API tanpa tombol di layar mana pun —
    itulah sebabnya 305 baris log tidak punya satu pun penilaian manual dan metrik efektivitas
    tidak pernah bisa dihitung (evaluasi pra-Fase 5 §5.4).
    """
    if not _require(user):
        return HTMLResponse("", status_code=status.HTTP_401_UNAUTHORIZED)
    p = db.get(models.Pengajuan, pengajuan_id)
    if p is None:
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Pengajuan tidak ditemukan.</div>",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if hasil_manual not in (models.HasilKelayakan.LAYAK, models.HasilKelayakan.TIDAK_LAYAK):
        return HTMLResponse(
            "<div class='alert alert-danger mb-0'>Pilihan verifikasi tidak sah.</div>",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    baris = verifikasi_service.rekam_verifikasi(
        db, p, hasil_manual, petugas_id=user.id, catatan=catatan.strip() or None
    )
    sepakat = baris.hasil_sistem == baris.hasil_manual
    return _toast(
        templates.TemplateResponse(
            request, "partials/_verifikasi.html", {"p": p, "verifikasi": baris}
        ),
        "Verifikasi terekam"
        + (" — sepakat dengan sistem." if sepakat else " — berbeda dari putusan sistem."),
        "good" if sepakat else "warn",
    )


@router.post("/detail/{pengajuan_id}/analisis", response_class=HTMLResponse)
def detail_analisis(
    pengajuan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(get_optional_user),
):
    if not _require(user):
        return HTMLResponse("", status_code=status.HTTP_401_UNAUTHORIZED)
    p = db.get(models.Pengajuan, pengajuan_id)
    if p is None or p.data_survei is None:
        return HTMLResponse(
            "<div class='alert alert-danger'>Data survei belum lengkap.</div>",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    hasil_analisis = pipeline.analisis_pengajuan(db, p)
    db.refresh(p)
    return _toast(
        templates.TemplateResponse(
            request, "partials/_hasil.html", {"p": p, "hasil": pipeline.susun_hasil(p)}
        ),
        f"Analisis selesai dalam {hasil_analisis['durasi_ms']} ms.",
    )


# ---- Ranking (HTMX) ----
@router.get("/peringkat", response_class=HTMLResponse)
def peringkat(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(get_optional_user),
):
    """Tampilkan batch terakhir yang TERSIMPAN — tanpa menghitung ulang.

    Sampai Fase 4 halaman ini selalu kosong dan satu-satunya cara melihat peringkat adalah
    menekan tombol yang menjalankan batch baru: 145 baris `ranking_topsis` tertulis setiap kali
    seseorang ingin melihat hasil kemarin (evaluasi pra-Fase 5 §5.5).
    """
    if not _require(user):
        return _redirect("/login")
    return templates.TemplateResponse(
        request,
        "peringkat.html",
        _ctx(user, hasil=_batch_terakhir(db)),
    )


def _batch_terakhir(db: Session) -> Optional[dict]:
    """Rakit batch perangkingan terakhir dari basis data (bukan menjalankan ulang Tier 3)."""
    batch_id = db.execute(
        select(models.RankingTopsis.batch_id)
        .order_by(models.RankingTopsis.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if batch_id is None:
        return None

    rows = db.execute(
        select(models.RankingTopsis)
        .where(models.RankingTopsis.batch_id == batch_id)
        .order_by(models.RankingTopsis.peringkat)
        .options(
            joinedload(models.RankingTopsis.pengajuan).joinedload(models.Pengajuan.warga)
        )
    ).scalars().all()
    log = db.execute(
        select(models.LogRanking).where(models.LogRanking.batch_id == batch_id)
    ).scalars().first()
    snapshot = (rows[0].bobot_snapshot or {}) if rows else {}

    return {
        "batch_id": batch_id,
        "jumlah_alternatif": len(rows),
        "versi_metode": snapshot.get("versi_metode"),
        "versi_konfigurasi": snapshot.get("versi_konfigurasi"),
        "durasi_ms": log.durasi_ms if log else None,
        "tersimpan": True,
        "dibuat": rows[0].created_at if rows else None,
        "ranking": [
            {
                "peringkat": r.peringkat,
                "pengajuan_id": r.pengajuan_id,
                "warga_nama": r.pengajuan.warga.nama,
                "nilai_preferensi": r.nilai_preferensi,
                "prediksi": models.HasilKelayakan.LAYAK,
                "skor_urgensi": round(pipeline._urgensi_pengajuan(r.pengajuan), 4),
                "seri_dengan": r.seri_dengan,
                "keanggotaan": r.keanggotaan,
            }
            for r in rows
        ],
    }


@router.post("/peringkat/run", response_class=HTMLResponse)
def peringkat_run(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(get_optional_user),
):
    if not _require(user):
        return HTMLResponse("", status_code=status.HTTP_401_UNAUTHORIZED)
    hasil = pipeline.jalankan_ranking(db)
    return _toast(
        templates.TemplateResponse(request, "partials/_ranking_table.html", {"hasil": hasil}),
        f"Batch {hasil['batch_id']} selesai — {hasil['jumlah_alternatif']} alternatif dirangking.",
    )


# ---- Metrik pengujian (Bab 9.2/9.3) ----
@router.get("/metrik", response_class=HTMLResponse)
def metrik(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(get_optional_user),
):
    if not _require(user):
        return _redirect("/login")
    return templates.TemplateResponse(
        request,
        "metrik.html",
        _ctx(user, eff=dashboard_service.efisiensi(db), efek=dashboard_service.efektivitas(db)),
    )


# ---- Form pengajuan baru ----
@router.get("/form", response_class=HTMLResponse)
def form_page(request: Request, user: Optional[models.User] = Depends(get_optional_user)):
    if not _require(user):
        return _redirect("/login")
    return templates.TemplateResponse(request, "form.html", _ctx(user, error=None))


@router.post("/form", response_class=HTMLResponse)
def form_submit(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(get_optional_user),
    nik: str = Form(...),
    nama: str = Form(...),
    usia: int = Form(...),
    jenis_kelamin: str = Form(...),
    status_pernikahan: str = Form(...),
    jumlah_tanggungan: int = Form(...),
    alamat: str = Form(default=""),
    pendapatan: float = Form(...),
    status_pekerjaan: str = Form(default=""),
    aset_produktif: Optional[str] = Form(default=None),
    riwayat_bantuan: Optional[str] = Form(default=None),
    luas_rumah: Optional[float] = Form(default=None),
    jenis_lantai: str = Form(default=""),
    jenis_dinding: str = Form(default=""),
    sumber_air: str = Form(default=""),
    isi_teks: str = Form(default=""),
    sumber_teks: str = Form(default="petugas"),
):
    if not _require(user):
        return _redirect("/login")
    try:
        payload = PengajuanCreate(
            warga=WargaIn(
                nik=nik,
                nama=nama,
                usia=usia,
                jenis_kelamin=jenis_kelamin,
                status_pernikahan=status_pernikahan,
                jumlah_tanggungan=jumlah_tanggungan,
                alamat=alamat or None,
            ),
            data_survei=DataSurveiIn(
                pendapatan=pendapatan,
                status_pekerjaan=status_pekerjaan or None,
                aset_produktif=aset_produktif is not None,
                riwayat_bantuan=riwayat_bantuan is not None,
                luas_rumah=luas_rumah,
                jenis_lantai=jenis_lantai or None,
                jenis_dinding=jenis_dinding or None,
                sumber_air=sumber_air or None,
            ),
            teks_naratif=(
                [TeksNaratifIn(sumber=sumber_teks, isi_teks=isi_teks)] if isi_teks.strip() else []
            ),
        )
    except ValidationError as exc:
        return templates.TemplateResponse(
            request,
            "form.html",
            _ctx(user, error=str(exc)),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    pengajuan = create_pengajuan(db, user.id, payload)
    return _redirect(f"/detail/{pengajuan.id}")
