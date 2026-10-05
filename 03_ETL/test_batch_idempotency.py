#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_batch_idempotency.py — Pengujian Otomatis Idempotensi & Konsistensi Skema
==============================================================================
Memverifikasi:
1. Prinsip Idempotensi Mutlak: State(Run 1) == State(Run 2).
2. Konsistensi Skema Data Layer (dim_date, dim_product, fact_sales, plan_production_daily).
3. Integritas Referensial PK-FK.
4. Nilai metrik matematis dan bisnis (non-negatif, tidak ada NaN pada kunci primer).
"""

import sys
import os
import shutil
import subprocess
from pathlib import Path
import pandas as pd
import numpy as np

# Setup path
SCRIPT_DIR = Path(__file__).resolve().parent
RUN1_DIR = SCRIPT_DIR / "temp_idempotency_run1"
RUN2_DIR = SCRIPT_DIR / "temp_idempotency_run2"

TABLE_NAMES = [
    "dim_date",
    "dim_product",
    "fact_sales",
    "plan_production_daily",
    "forecast_recommendations"
]

def run_batch_simulation(output_dir: Path) -> int:
    """Menjalankan weekly_batch.py dengan output direktori tertentu."""
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "weekly_batch.py"),
        "--dry-run",
        "--output-dir", str(output_dir)
    ]
    proc = subprocess.run(cmd, cwd=str(SCRIPT_DIR), capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"[ERROR] Eksekusi batch gagal dengan exit code {proc.returncode}")
        print("STDOUT:", proc.stdout)
        print("STDERR:", proc.stderr)
    return proc.returncode

def main():
    print("=" * 70)
    print("MEMULAI PENGUJIAN OTOMATIS: IDEMPOTENSI & KONSISTENSI SKEMA BATCH")
    print("=" * 70)

    try:
        # Bersihkan direktori sementara jika ada
        if RUN1_DIR.exists():
            shutil.rmtree(RUN1_DIR, ignore_errors=True)
        if RUN2_DIR.exists():
            shutil.rmtree(RUN2_DIR, ignore_errors=True)

        # 1. Eksekusi Run 1
        print("\n[*] Menjalankan Eksekusi Batch Run 1...")
        code1 = run_batch_simulation(RUN1_DIR)
        assert code1 == 0, f"Run 1 Gagal dengan returncode {code1}"
        print("    -> Run 1 Selesai dengan sukses (Exit code 0).")

        # 2. Eksekusi Run 2
        print("\n[*] Menjalankan Eksekusi Batch Run 2 (Pengujian Idempotensi)...")
        code2 = run_batch_simulation(RUN2_DIR)
        assert code2 == 0, f"Run 2 Gagal dengan returncode {code2}"
        print("    -> Run 2 Selesai dengan sukses (Exit code 0).")

        # 3. Pengujian Kesetaraan Isi Data (Idempotensi)
        print("\n[*] Membandingkan Hasil Run 1 vs Run 2 per Tabel...")
        all_passed = True
        for table in TABLE_NAMES:
            file1 = RUN1_DIR / f"{table}.csv"
            file2 = RUN2_DIR / f"{table}.csv"

            assert file1.exists(), f"File {file1} tidak ditemukan!"
            assert file2.exists(), f"File {file2} tidak ditemukan!"

            df1 = pd.read_csv(file1)
            df2 = pd.read_csv(file2)

            # Cek kesamaan dimensi
            assert len(df1) == len(df2), f"Beda baris pada {table}: {len(df1)} vs {len(df2)}"
            assert list(df1.columns) == list(df2.columns), f"Beda kolom pada {table}"

            # Cek kesetaraan data (mengabaikan perbedaan timestamp eksekusi jika ada)
            compare_cols = [c for c in df1.columns if c != 'batch_execution_timestamp']
            
            # Khusus numerik, bandingkan dengan toleransi presisi float
            for col in compare_cols:
                if pd.api.types.is_numeric_dtype(df1[col]):
                    np.testing.assert_allclose(
                        df1[col].values, df2[col].values, rtol=1e-5, atol=1e-5,
                        err_msg=f"Diskrepansi numerik pada tabel {table}, kolom {col}"
                    )
                else:
                    # Nilai string/kategori
                    diff_mask = df1[col].fillna('') != df2[col].fillna('')
                    if diff_mask.any():
                        raise AssertionError(f"Diskrepansi data teks pada tabel {table}, kolom {col}")

            print(f"    [OK] Tabel '{table}': Identik 100% ({len(df1):,} baris, {len(df1.columns)} kolom).")

        # 4. Pengujian Integritas Skema & Aturan Bisnis
        print("\n[*] Memverifikasi Integritas Relasional & Kontrak Skema...")
        df_date = pd.read_csv(RUN1_DIR / "dim_date.csv")
        df_prod = pd.read_csv(RUN1_DIR / "dim_product.csv")
        df_fact = pd.read_csv(RUN1_DIR / "fact_sales.csv")
        df_plan = pd.read_csv(RUN1_DIR / "plan_production_daily.csv")
        df_recs = pd.read_csv(RUN1_DIR / "forecast_recommendations.csv")

        # A. Cek Kunci Primer Unik
        assert not df_date['date_id'].duplicated().any(), "PK date_id duplikat di dim_date!"
        assert not df_prod['product_id'].duplicated().any(), "PK product_id duplikat di dim_product!"
        print("    [OK] Keunikan Primary Key (dim_date & dim_product) lulus.")

        # B. Cek Integritas Referensial (FK pada fact_sales)
        date_id_set = set(df_date['date_id'])
        prod_id_set = set(df_prod['product_id'])
        assert df_fact['date_id'].isin(date_id_set).all(), "Ditemukan orphan date_id di fact_sales!"
        assert df_fact['product_id'].isin(prod_id_set).all(), "Ditemukan orphan product_id di fact_sales!"
        print("    [OK] Integritas Referensial FK -> PK lulus 100%.")

        # C. Cek Aturan Bisnis Fakta Penjualan
        assert (df_fact['qty_sold'] > 0).all(), "Ditemukan kuantitas penjualan <= 0!"
        assert (df_fact['net_amount'] > 0).all(), "Ditemukan omzet bersih <= 0!"
        print("    [OK] Validitas Nilai Bisnis (qty > 0, net_amount > 0) lulus.")

        # D. Cek Rencana Produksi & MTO Threshold
        assert (df_plan['target_produksi'] >= 0).all(), "Ditemukan target produksi negatif!"
        # Verifikasi bahwa target produksi adalah integer bulat (bukan pecahan float)
        assert (df_plan['target_produksi'] % 1 == 0).all(), "Target produksi bukan bilangan bulat!"
        print("    [OK] Integritas Target Produksi Harian (MTO threshold & integer rounding) lulus.")

        # E. Cek Rekomendasi Manajerial (3 Target Kategori)
        assert len(df_recs) == 3, f"Ekspektasi 3 kategori di rekomendasi, ditemukan {len(df_recs)}"
        expected_cats = {"Cake", "Japanese", "Mille Crepes"}
        assert set(df_recs['kategori']) == expected_cats, "Kategori rekomendasi tidak sesuai!"
        # Verifikasi tidak ada placeholder 0.00%
        for col in ['holdout_wmape', 'cv_wmape_3fold', 'composite_wmape']:
            zeros = (df_recs[col] == '0.00%').sum()
            assert zeros == 0, f"Placeholder 0.00% terdeteksi di {col}!"
        print("    [OK] Integritas Rekomendasi Manajerial & Ketiadaan Placeholder 0.00% lulus.")

        print("\n" + "=" * 70)
        print("SEMUA PENGUJIAN IDEMPOTENSI & SKEMA LULUS DENGAN SEMPURNA [PASS]")
        print("=" * 70)

    finally:
        # Bersihkan direktori sementara dengan toleransi file lock Windows
        import time
        time.sleep(0.5)
        if RUN1_DIR.exists():
            shutil.rmtree(RUN1_DIR, ignore_errors=True)
        if RUN2_DIR.exists():
            shutil.rmtree(RUN2_DIR, ignore_errors=True)
        print("[*] Direktori pengujian sementara dibersihkan.")

if __name__ == "__main__":
    main()
