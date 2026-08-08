"""fase 5: instrumen pengujian (durasi per tier, log batch Tier 3, verifikasi manual)

Revision ID: 9a1c4f7be210
Revises: 7db13cef0250
Create Date: 2026-08-08

Tiga perubahan, ketiganya keputusan Fase 5 (evaluasi pra-Fase 5 §5.2–§5.4):

D-03  durasi per tier + penanda cold/warm di `log_pengujian`, dan tabel `log_ranking` untuk
      durasi Tier 3 yang bersatuan PER BATCH, bukan per pengajuan.
D-04  `verifikasi_manual` berdiri sendiri, membawa SNAPSHOT putusan sistem yang benar-benar
      dinilai petugas. Kolom `log_pengujian.hasil_manual_petugas` dihapus: menumpangkan
      penilaian manusia pada baris log terbaru membuat pasangan (sistem, manual) memakai
      putusan lama setelah analisis ulang, atau hilang sama sekali bila verifikasi
      mendahului analisis. Kolom itu berisi 0 baris di seluruh basis data, jadi tidak ada
      data yang berpindah — inilah momen termurah untuk memindahkannya.
D-01/OI-07  kolom bahan penjelasan Tier 3 di `ranking_topsis` (jarak, seri, label keanggotaan);
      keempatnya sudah dihitung sejak Fase 4 lalu dibuang sebelum disimpan.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9a1c4f7be210"
down_revision: Union[str, None] = "7db13cef0250"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- log_pengujian: durasi per tier + penanda pemuatan model (D-03/D-02) ---
    with op.batch_alter_table("log_pengujian") as batch:
        batch.add_column(sa.Column("durasi_tier1_ms", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("durasi_tier2_ms", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("jenis_muat", sa.String(length=8), nullable=True))
        batch.drop_column("hasil_manual_petugas")

    # --- ranking_topsis: bahan penjelasan Tier 3 (OI-07) ---
    with op.batch_alter_table("ranking_topsis") as batch:
        batch.add_column(sa.Column("jarak_positif", sa.Float(), nullable=True))
        batch.add_column(sa.Column("jarak_negatif", sa.Float(), nullable=True))
        batch.add_column(sa.Column("seri_dengan", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("keanggotaan", sa.JSON(), nullable=True))

    # --- log_ranking: durasi Tier 3 per batch (D-03) ---
    op.create_table(
        "log_ranking",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.String(length=64), nullable=False),
        sa.Column("jumlah_alternatif", sa.Integer(), nullable=False),
        sa.Column("durasi_ms", sa.Integer(), nullable=False),
        sa.Column("versi_metode", sa.String(length=64), nullable=False),
        sa.Column("versi_konfigurasi", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_log_ranking_batch_id"), "log_ranking", ["batch_id"])

    # --- verifikasi_manual: penilaian petugas + snapshot putusan yang dinilai (D-04) ---
    op.create_table(
        "verifikasi_manual",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pengajuan_id", sa.Integer(), nullable=False),
        sa.Column("petugas_id", sa.Integer(), nullable=True),
        sa.Column("hasil_manual", sa.String(length=16), nullable=False),
        sa.Column("hasil_sistem", sa.String(length=16), nullable=True),
        sa.Column("probabilitas_sistem", sa.Float(), nullable=True),
        sa.Column("versi_model", sa.String(length=64), nullable=True),
        sa.Column("peringkat_sistem", sa.Integer(), nullable=True),
        sa.Column("catatan", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["pengajuan_id"], ["pengajuan.id"]),
        sa.ForeignKeyConstraint(["petugas_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_verifikasi_manual_pengajuan_id"), "verifikasi_manual", ["pengajuan_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_verifikasi_manual_pengajuan_id"), table_name="verifikasi_manual")
    op.drop_table("verifikasi_manual")
    op.drop_index(op.f("ix_log_ranking_batch_id"), table_name="log_ranking")
    op.drop_table("log_ranking")

    with op.batch_alter_table("ranking_topsis") as batch:
        batch.drop_column("keanggotaan")
        batch.drop_column("seri_dengan")
        batch.drop_column("jarak_negatif")
        batch.drop_column("jarak_positif")

    with op.batch_alter_table("log_pengujian") as batch:
        batch.add_column(sa.Column("hasil_manual_petugas", sa.String(length=16), nullable=True))
        batch.drop_column("jenis_muat")
        batch.drop_column("durasi_tier2_ms")
        batch.drop_column("durasi_tier1_ms")
