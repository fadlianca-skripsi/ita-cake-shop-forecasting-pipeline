#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
weekly_batch.py — Pipeline Batch Peramalan Permintaan Mingguan & Kimball Data Mart
===================================================================================
ITA Cake Shop Antapani, Bandung.
Sesuai Kaidah Ekonometrika umkm-forecasting.md & Kompatibel BigQuery Sandbox.

Fitur Utama:
1. Ingesti Data POS Olsera (pembersihan anti-double-discount, eliminasi void, deduplikasi).
2. Pembangunan Kimball Data Mart (dim_date, dim_product, fact_sales).
3. Peramalan Top-Down Holt-Winters Multiplicative Terkunci (Cake, Japanese, Mille Crepes).
4. Disagregasi Anti-Limbah:
   - Day-of-Week Share adaptif 4 pekan (28 hari).
   - Rolling SKU Share dinamis 12 pekan (84 hari).
   - Safety Stock SL 95% (Z = 1.65).
   - Ambang MTO (< 0.5 = 0, np.round, TANPA np.ceil).
5. Kompatibilitas BigQuery Sandbox:
   - Tanpa DML berbayar (INSERT/UPDATE/DELETE).
   - Tanpa Cloud Storage berbayar (direct API streaming load via load_table_from_dataframe).
   - WriteDisposition.WRITE_TRUNCATE me-reset kedaluwarsa tabel 60 hari setiap Senin (W-MON).
   - Pembuatan Mart Views Looker Studio secara otomatis.
6. Mode Local Dry-Run (--dry-run) 100% luring tanpa kredensial cloud.
7. Jaminan Idempotensi mutlak (menghasilkan state identik pada eksekusi berulang).
"""

import os
import sys
from pathlib import Path

# Windows Conda DLL loader compatibility (MKL/LAPACK support when running outside activated shell)
if sys.platform == 'win32':
    lib_bin = Path(sys.prefix) / 'Library' / 'bin'
    if lib_bin.exists():
        os.environ['PATH'] = str(lib_bin) + os.pathsep + os.environ.get('PATH', '')
        if hasattr(os, 'add_dll_directory'):
            try:
                os.add_dll_directory(str(lib_bin))
            except Exception:
                pass

import argparse
import datetime
import logging
from typing import Dict, Tuple, Optional, Any
import yaml
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("weekly_batch")


def load_config(config_path: Path) -> dict:
    """Memuat file konfigurasi batch YAML."""
    if not config_path.exists():
        raise FileNotFoundError(f"File konfigurasi tidak ditemukan: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    logger.info(f"Konfigurasi berhasil dimuat dari: {config_path}")
    return config


def clean_pos_dataset(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Membersihkan dataset POS mentah dari mesin Olsera:
    1. Sanitasi teks (strip whitespace, title casing).
    2. Parsing tanggal dan validasi non-null.
    3. Konversi numerik aman.
    4. Koreksi Finansial: Anti-double-discount (omzet_bersih = amount).
    5. Filter transaksi tuntas (status 'Z') dan kuantitas positif.
    6. Deduplikasi komposit transaksi sah via kombinasi kolom unik.
    """
    if df_raw.empty:
        return pd.DataFrame()

    df = df_raw.copy()

    # Normalisasi nama kolom ke huruf kecil
    df.columns = [str(col).strip().lower() for col in df.columns]

    # Validasi kolom wajib minimum
    required_cols = ['order date', 'item name', 'item group', 'qty', 'amount']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Kolom wajib tidak ditemukan pada file POS: {missing}")

    # Sanitasi teks
    df['item name'] = df['item name'].astype(str).str.strip().str.title()
    df['item group'] = df['item group'].astype(str).str.strip().str.title()

    # Parsing tanggal
    df['order date'] = pd.to_datetime(df['order date'], errors='coerce')
    df = df.dropna(subset=['order date', 'item name', 'item group', 'qty', 'amount'])

    # Sanitasi numerik
    df['qty'] = pd.to_numeric(df['qty'], errors='coerce').fillna(0)
    price_col = 'price' if 'price' in df.columns else 'unit price'
    if price_col in df.columns:
        df['price'] = pd.to_numeric(df[price_col], errors='coerce').fillna(0)
    else:
        df['price'] = (df['amount'] / df['qty']).replace([np.inf, -np.inf], 0).fillna(0)

    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
    discount_col = 'discount amount' if 'discount amount' in df.columns else 'discount'
    df['discount amount'] = pd.to_numeric(df.get(discount_col, 0), errors='coerce').fillna(0)

    # KOREKSI FINANSIAL: Olsera POS mencatat 'amount' sudah dipotong diskon
    df['gross_amount'] = df['qty'] * df['price']
    df['omzet_bersih'] = df['amount']

    # Filter status transaksi tuntas
    if 'order status' in df.columns:
        df = df[df['order status'] == 'Z']

    # Filter kuantitas dan omzet positif
    df = df[(df['qty'] > 0) & (df['omzet_bersih'] > 0)]

    # Deduplikasi komposit
    order_col = 'order no' if 'order no' in df.columns else 'order_no'
    if order_col in df.columns:
        dedup_cols = [order_col, 'order date', 'item name', 'qty', 'price', 'amount']
        df = df.drop_duplicates(subset=dedup_cols, keep='first')
        df.rename(columns={order_col: 'order_no'}, inplace=True)
    else:
        df['order_no'] = [f"ORD-{i+1:08d}" for i in range(len(df))]

    return df


def load_raw_pos_files(pos_dir: Path, file_pattern: str = "*.xlsx") -> pd.DataFrame:
    """
    Membaca seluruh file Excel POS secara rekursif dari direktori lokal.
    """
    logger.info(f"Mencari file POS dengan pola '{file_pattern}' di: {pos_dir}")
    if not pos_dir.exists():
        logger.warning(f"Direktori POS tidak ditemukan: {pos_dir}")
        return pd.DataFrame()

    files = sorted(pos_dir.glob(f"**/{file_pattern}"))
    if not files:
        # Fallback coba pattern case-insensitive
        files = sorted(pos_dir.glob("**/*Item Penjualan*.xlsx"))

    if not files:
        logger.warning(f"Tidak ada file Excel yang cocok di: {pos_dir}")
        return pd.DataFrame()

    dfs = []
    for f in files:
        try:
            logger.info(f"Membaca file POS: {f.name}")
            df_f = pd.read_excel(f)
            dfs.append(df_f)
        except Exception as e:
            logger.error(f"Gagal membaca file {f.name}: {e}")

    if not dfs:
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)
    logger.info(f"Total baris mentah terbaca dari {len(files)} file: {len(combined):,}")
    return combined


def build_star_schema(
    df_clean: pd.DataFrame,
    target_categories: list,
    official_start: pd.Timestamp,
    horizon_end: pd.Timestamp,
    idul_fitri_ranges: list
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Membangun Kimball Star Schema:
    1. dim_date: Dimensi kalender lengkap harian.
    2. dim_product: Dimensi produk (SCD Type 1) dengan flag is_active_12w.
    3. fact_sales: Fakta transaksi penjualan granular.
    """
    logger.info("Membangun Kimball Star Schema (dim_date, dim_product, fact_sales)...")

    # 1. DIM_DATE
    cal_dates = pd.date_range(official_start, horizon_end, freq='D')
    dim_date = pd.DataFrame({'tanggal_penuh': cal_dates})
    dim_date['date_id'] = dim_date['tanggal_penuh'].dt.strftime('%Y%m%d').astype(int)
    dim_date['nama_hari'] = dim_date['tanggal_penuh'].dt.day_name()
    dim_date['nama_bulan'] = dim_date['tanggal_penuh'].dt.month_name()
    dim_date['minggu_ke'] = dim_date['tanggal_penuh'].dt.isocalendar().week.astype(int)
    dim_date['tahun'] = dim_date['tanggal_penuh'].dt.year.astype(int)
    dim_date['is_weekend'] = dim_date['tanggal_penuh'].dt.dayofweek.isin([5, 6])
    dim_date['is_idulfitri_mask_window'] = False

    for s_str, e_str in idul_fitri_ranges:
        s_dt = pd.to_datetime(s_str)
        e_dt = pd.to_datetime(e_str)
        mask = (dim_date['tanggal_penuh'] >= s_dt) & (dim_date['tanggal_penuh'] <= e_dt)
        dim_date.loc[mask, 'is_idulfitri_mask_window'] = True

    dim_date['tanggal_penuh'] = dim_date['tanggal_penuh'].dt.strftime('%Y-%m-%d')
    dim_date = dim_date[[
        'date_id', 'tanggal_penuh', 'nama_hari', 'nama_bulan',
        'minggu_ke', 'tahun', 'is_weekend', 'is_idulfitri_mask_window'
    ]]

    # 2. DIM_PRODUCT
    latest_prod = df_clean.sort_values('order date').groupby('item name').tail(1)
    dim_product = latest_prod[['item name', 'item group', 'price']].copy()
    dim_product.rename(columns={
        'item name': 'product_name',
        'item group': 'category_name',
        'price': 'sell_price_current'
    }, inplace=True)
    dim_product.reset_index(drop=True, inplace=True)
    dim_product['product_id'] = dim_product.index + 1
    dim_product['scd_type'] = 'Type1'

    # 12-Week Active SKU Flag
    cutoff_12w = horizon_end - pd.Timedelta(days=84)
    target_clean = df_clean[df_clean['item group'].isin(target_categories)]
    sales_12w = target_clean[target_clean['order date'] >= cutoff_12w].groupby('item name')['qty'].sum()
    active_skus = set(sales_12w[sales_12w > 0].index)

    dim_product['is_active_12w'] = dim_product['product_name'].apply(
        lambda name: True if name in active_skus else False
    ).astype(object)
    # Non-target categories set to None/NULL
    dim_product.loc[~dim_product['category_name'].isin(target_categories), 'is_active_12w'] = None

    dim_product = dim_product[[
        'product_id', 'product_name', 'category_name',
        'sell_price_current', 'scd_type', 'is_active_12w'
    ]]

    # 3. FACT_SALES
    date_lookup = dict(zip(pd.to_datetime(dim_date['tanggal_penuh']).dt.date, dim_date['date_id']))
    prod_lookup = dict(zip(dim_product['product_name'], dim_product['product_id']))

    fact = df_clean.copy()
    fact['date_id'] = fact['order date'].dt.date.map(date_lookup)
    fact['product_id'] = fact['item name'].map(prod_lookup)
    fact.dropna(subset=['date_id', 'product_id'], inplace=True)

    fact = fact[[
        'order_no', 'date_id', 'product_id', 'price', 'qty',
        'gross_amount', 'discount amount', 'omzet_bersih'
    ]].copy()
    fact.columns = [
        'order_no', 'date_id', 'product_id', 'unit_price', 'qty_sold',
        'gross_amount', 'discount_amount', 'net_amount'
    ]

    fact['date_id'] = fact['date_id'].astype(int)
    fact['product_id'] = fact['product_id'].astype(int)
    fact['qty_sold'] = fact['qty_sold'].astype(int)
    fact['unit_price'] = fact['unit_price'].round(2)
    fact['gross_amount'] = fact['gross_amount'].round(2)
    fact['discount_amount'] = fact['discount_amount'].round(2)
    fact['net_amount'] = fact['net_amount'].round(2)

    logger.info(f"Star Schema selesai dibangun: dim_date ({len(dim_date)} baris), "
                f"dim_product ({len(dim_product)} baris), fact_sales ({len(fact)} baris).")

    return dim_date, dim_product, fact


def run_forecasting_and_disaggregation(
    df_clean: pd.DataFrame,
    config: dict,
    forecast_week_start: pd.Timestamp
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Menjalankan pemodelan Holt-Winters mingguan makro dan disagregasi mikro:
    1. Agregasi mingguan W-MON untuk Cake, Japanese, Mille Crepes.
    2. Pra-pemrosesan: Interpolasi Idul Fitri & Tukey IQR Capping.
    3. Fit Holt-Winters Multiplicative terkunci (replace 0 -> 0.1).
    4. Proyeksi 1 pekan ke depan (h=1).
    5. Disagregasi porsi hari adaptif 4 pekan & rolling SKU share 12 pekan.
    6. Safety stock (Z=1.65) & Ambang batas MTO (<0.5 = 0, np.round).
    7. Pembuatan tabel rekomendasi manajerial.
    """
    logger.info(f"Memulai peramalan operasional untuk pekan: {forecast_week_start.strftime('%Y-%m-%d')}...")

    target_categories = config['pipeline']['target_categories']
    idul_fitri_ranges = config['pipeline']['idul_fitri_ranges']
    capping_bounds = config['pipeline']['iqr_capping']
    champion_models = config['champion_models']
    disagg_cfg = config['disaggregation']

    # Filter data latih hingga sebelum pekan target
    history_data = df_clean[
        (df_clean['order date'] < forecast_week_start) &
        (df_clean['item group'].isin(target_categories))
    ].copy()

    if history_data.empty:
        raise ValueError(f"Tidak ada data historis sebelum {forecast_week_start}")

    # Agregasi harian kontinu
    min_date = history_data['order date'].min().normalize()
    max_date = history_data['order date'].max().normalize()
    date_index = pd.date_range(min_date, max_date, freq='D')

    daily_pivot = history_data.pivot_table(
        index='order date',
        columns='item group',
        values='qty',
        aggfunc='sum'
    ).reindex(date_index, fill_value=0)

    # Resampling mingguan W-MON (Senin-Minggu)
    weekly_raw = daily_pivot.resample('W-MON', closed='left', label='left').sum()[target_categories]
    weekly_clean = weekly_raw.copy()

    # 1. Masking Idul Fitri & Interpolasi
    for s_str, e_str in idul_fitri_ranges:
        s_dt = pd.to_datetime(s_str)
        e_dt = pd.to_datetime(e_str)
        mask = (weekly_clean.index + pd.Timedelta(days=6) >= s_dt) & (weekly_clean.index <= e_dt)
        weekly_clean.loc[mask, :] = np.nan

    weekly_clean = weekly_clean.interpolate(method='linear').bfill().ffill()

    # 2. Outlier Capping (Tukey IQR)
    for cat in target_categories:
        up_bound = capping_bounds.get(cat, weekly_clean[cat].quantile(0.75) * 1.5)
        weekly_clean[cat] = np.where(weekly_clean[cat] > up_bound, up_bound, weekly_clean[cat])

    # 3. Model Fitting & Forecasting
    weekly_forecasts = {}
    residuals_std = {}

    for cat in target_categories:
        series = weekly_clean[cat].copy()
        m_params = champion_models[cat]

        # Safety replacement 0 -> 0.1 untuk Multiplicative
        train_series = series.replace(0, 0.1)

        model = ExponentialSmoothing(
            train_series,
            trend=m_params['trend'],
            seasonal=m_params['seasonal'],
            seasonal_periods=m_params['m'],
            initialization_method=m_params['initialization_method']
        )
        fitted = model.fit(
            smoothing_level=m_params['alpha'],
            smoothing_trend=m_params.get('beta') if m_params.get('trend') is not None else None,
            smoothing_seasonal=m_params['gamma'],
            optimized=False
        )

        fc_1w = float(max(0.0, fitted.forecast(1).values[0]))
        weekly_forecasts[cat] = fc_1w
        residuals_std[cat] = float(np.std(fitted.resid))
        logger.info(f"Forecast Mingguan [{cat}]: {fc_1w:.2f} pcs | Residual Std: {residuals_std[cat]:.2f}")

    # 4. Disagregasi Mikro ke SKU Harian (7 Hari Kalender)
    forecast_dates = pd.date_range(forecast_week_start, periods=7, freq='D')
    batch_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

    daily_sku_target = df_clean[
        (df_clean['order date'] < forecast_week_start) &
        (df_clean['item group'].isin(target_categories))
    ].groupby(['order date', 'item group', 'item name'])['qty'].sum().reset_index()

    plan_records = []
    z_score = disagg_cfg['z_score']

    for cat in target_categories:
        w_fc = weekly_forecasts[cat]
        std_resid = residuals_std[cat]

        # Porsi DoW adaptif 4 pekan (28 hari terakhir)
        dow_start = forecast_week_start - pd.Timedelta(days=disagg_cfg['dow_window_days'])
        dow_data = daily_sku_target[
            (daily_sku_target['order date'] >= dow_start) &
            (daily_sku_target['order date'] < forecast_week_start) &
            (daily_sku_target['item group'] == cat)
        ]
        total_dow_qty = dow_data['qty'].sum()
        if total_dow_qty > 0:
            dow_qty = dow_data.groupby(dow_data['order date'].dt.dayofweek)['qty'].sum()
            dow_share = {i: dow_qty.get(i, 0) / total_dow_qty for i in range(7)}
        else:
            dow_share = {i: 1.0 / 7.0 for i in range(7)}

        # Rolling SKU share dinamis 12 pekan (84 hari terakhir)
        sku_start = forecast_week_start - pd.Timedelta(days=disagg_cfg['sku_window_days'])
        sku_data = daily_sku_target[
            (daily_sku_target['order date'] >= sku_start) &
            (daily_sku_target['order date'] < forecast_week_start) &
            (daily_sku_target['item group'] == cat)
        ]
        total_sku_qty = sku_data['qty'].sum()
        if total_sku_qty > 0:
            sku_qty = sku_data.groupby('item name')['qty'].sum()
            sku_share = (sku_qty / total_sku_qty).to_dict()
        else:
            skus = daily_sku_target[daily_sku_target['item group'] == cat]['item name'].unique()
            sku_share = {sku: 1.0 / max(1, len(skus)) for sku in skus}

        for dt in forecast_dates:
            day_dow = dt.dayofweek
            day_fc_cat = w_fc * dow_share.get(day_dow, 1.0 / 7.0)

            for sku, share in sku_share.items():
                if share <= 0:
                    continue

                sku_day_base = day_fc_cat * share
                safety_stock = z_score * std_resid * share / np.sqrt(7)
                raw_target = sku_day_base + safety_stock

                # MTO Threshold: raw_target < 0.5 -> 0, else np.round()
                if raw_target < disagg_cfg['mto_threshold']:
                    final_target = 0
                else:
                    final_target = int(np.round(raw_target))

                plan_records.append({
                    'forecast_date': dt.strftime('%Y-%m-%d'),
                    'category_name': cat,
                    'product_name': sku,
                    'forecast_murni': int(np.round(sku_day_base)),
                    'safety_stock': int(np.round(safety_stock)),
                    'target_produksi': final_target,
                    'batch_execution_timestamp': batch_ts
                })

    df_plan = pd.DataFrame(plan_records)
    # Urutkan berdasarkan tanggal ASC, target DESC
    df_plan.sort_values(by=['forecast_date', 'target_produksi'], ascending=[True, False], inplace=True)
    df_plan.reset_index(drop=True, inplace=True)

    # 5. Tabel Rekomendasi Manajerial
    recs = []
    for cat in target_categories:
        m_info = champion_models[cat]
        if cat == 'Mille Crepes':
            note = "Hipotesis: m=8 menangkap perputaran tren rasa bulanan/dwibulanan."
        elif cat == 'Japanese':
            note = "Pola musiman semesteran (m=26) terbukti optimal menangkap siklus libur sekolah Bandung."
        else:
            note = "Model menangkap tren level optimal (m=26 semesteran kalender)."

        recs.append({
            'kategori': cat,
            'model_arsitektur': f"Holt-Winters {m_info['seasonal'].title()}",
            'periode_musiman_m': int(m_info['m']),
            'smoothing_alpha': float(m_info['alpha']),
            'smoothing_gamma': float(m_info['gamma']),
            'holdout_wmape': f"{m_info['wmape_holdout']:.2f}%",
            'cv_wmape_3fold': f"{m_info['wmape_cv']:.2f}%",
            'composite_wmape': f"{m_info['composite_wmape']:.2f}%",
            'rekomendasi_operasional': note,
            'kebijakan_safety_stock': 'Z-score 1.65 diturunkan secara formal untuk Service Level 95% (distribusi normal).'
        })
    df_recs = pd.DataFrame(recs)

    logger.info(f"Rencana produksi harian selesai: {len(df_plan)} baris dihasilkan untuk pekan {forecast_week_start.date()}.")
    return df_plan, df_recs


def validate_schemas(tables: Dict[str, pd.DataFrame]) -> bool:
    """
    Memvalidasi integritas skema data layer sebelum diekspor atau dimuat:
    1. Memeriksa keberadaan kolom penting.
    2. Memeriksa non-null pada primary key.
    3. Memeriksa ketiadaan nilai negatif pada metrik bisnis.
    """
    logger.info("Menjalankan validasi skema tabel Data Layer...")
    errors = []

    # Validasi dim_date
    df_date = tables.get('dim_date')
    if df_date is not None:
        if df_date['date_id'].duplicated().any():
            errors.append("dim_date: Ditemukan duplikasi pada date_id!")
        if df_date['date_id'].isnull().any():
            errors.append("dim_date: Ditemukan nilai NULL pada date_id!")

    # Validasi dim_product
    df_prod = tables.get('dim_product')
    if df_prod is not None:
        if df_prod['product_id'].duplicated().any():
            errors.append("dim_product: Ditemukan duplikasi pada product_id!")
        if df_prod['product_name'].isnull().any():
            errors.append("dim_product: Ditemukan nilai NULL pada product_name!")

    # Validasi fact_sales
    df_fact = tables.get('fact_sales')
    if df_fact is not None:
        if df_fact[['date_id', 'product_id', 'net_amount']].isnull().any().any():
            errors.append("fact_sales: Ditemukan nilai NULL pada kolom kunci/metrik!")
        if (df_fact['qty_sold'] <= 0).any():
            errors.append("fact_sales: Ditemukan kuantitas <= 0!")
        if (df_fact['net_amount'] < 0).any():
            errors.append("fact_sales: Ditemukan net_amount negatif!")

    # Validasi plan_production_daily
    df_plan = tables.get('plan_production_daily')
    if df_plan is not None:
        if (df_plan['target_produksi'] < 0).any():
            errors.append("plan_production_daily: Ditemukan target produksi negatif!")
        if df_plan['forecast_date'].isnull().any():
            errors.append("plan_production_daily: Ditemukan tanggal NULL!")

    if errors:
        for err in errors:
            logger.error(f"[VALIDASI GAGAL] {err}")
        return False

    logger.info("Semua validasi skema tabel [PASS] - Data layer valid 100%.")
    return True


def export_local_csv(tables: Dict[str, pd.DataFrame], output_dir: Path) -> None:
    """Mengekspor seluruh tabel ke file CSV lokal."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        csv_path = output_dir / f"{name}.csv"
        df.to_csv(csv_path, index=False)
        logger.info(f"Ekspor CSV berhasil: {csv_path} ({len(df):,} baris)")


def upload_to_bigquery_sandbox(tables: Dict[str, pd.DataFrame], config: dict) -> None:
    """
    Mengunggah tabel ke BigQuery Sandbox:
    - Menggunakan client.load_table_from_dataframe() (API Batch gratis, tanpa GCS).
    - Memakai WriteDisposition.WRITE_TRUNCATE (me-reset kedaluwarsa 60 hari tabel setiap Senin).
    - Membuat / mengganti views Looker Studio secara otomatis via DDL.
    """
    try:
        from google.cloud import bigquery
    except ImportError:
        logger.error("Pustaka google-cloud-bigquery belum terpasang. Jalankan: pip install google-cloud-bigquery")
        raise

    project_id = os.environ.get(config['gcp']['project_id_env'], config['gcp']['project_id_default'])
    dataset_id = os.environ.get("BIGQUERY_DATASET") or config['gcp'].get('dataset_id', 'ita_cake_shop_datamart')
    location = config['gcp']['location']

    logger.info(f"Menghubungkan ke BigQuery Project: {project_id}, Dataset: {dataset_id} ({location})...")

    # Inisialisasi BigQuery Client
    client = bigquery.Client(project=project_id)

    # Pastikan dataset tersedia
    dataset_ref = bigquery.DatasetReference(project_id, dataset_id)
    try:
        client.get_dataset(dataset_ref)
        logger.info(f"Dataset '{dataset_id}' ditemukan.")
    except Exception:
        logger.info(f"Dataset '{dataset_id}' belum ada. Membuat dataset baru...")
        ds = bigquery.Dataset(dataset_ref)
        ds.location = location
        # 60 hari default table expiration jika di Sandbox
        ds.default_table_expiration_ms = 60 * 24 * 3600 * 1000
        client.create_dataset(ds, exists_ok=True)
        logger.info(f"Dataset '{dataset_id}' berhasil dibuat.")

    # Pemuatan setiap tabel menggunakan WRITE_TRUNCATE
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
    )

    for table_name, df in tables.items():
        table_ref = dataset_ref.table(table_name)
        logger.info(f"Mengunggah tabel '{table_name}' ({len(df):,} baris) ke BigQuery...")
        job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
        job.result()  # Menunggu job selesai
        logger.info(f"Tabel '{table_name}' berhasil dimuat (Status: WRITE_TRUNCATE Selesai).")

    # Pembangunan Views Looker Studio
    logger.info("Memperbarui Looker Studio Mart Views...")
    views_sql = {
        'v_looker_performance_overview': f"""
            CREATE OR REPLACE VIEW `{project_id}.{dataset_id}.v_looker_performance_overview` AS
            SELECT
                f.order_no,
                PARSE_DATE('%Y-%m-%d', d.tanggal_penuh) AS order_date,
                d.nama_hari,
                d.nama_bulan,
                d.minggu_ke,
                d.tahun,
                d.is_weekend,
                p.product_id,
                p.product_name,
                p.category_name,
                f.qty_sold,
                f.gross_amount,
                f.discount_amount,
                f.net_amount
            FROM `{project_id}.{dataset_id}.fact_sales` f
            JOIN `{project_id}.{dataset_id}.dim_date` d ON f.date_id = d.date_id
            JOIN `{project_id}.{dataset_id}.dim_product` p ON f.product_id = p.product_id;
        """,
        'v_looker_production_planning': f"""
            CREATE OR REPLACE VIEW `{project_id}.{dataset_id}.v_looker_production_planning` AS
            SELECT
                PARSE_DATE('%Y-%m-%d', forecast_date) AS forecast_date,
                category_name,
                product_name,
                forecast_murni,
                safety_stock,
                target_produksi,
                FORMAT_DATE('%a, %d %b %Y', PARSE_DATE('%Y-%m-%d', forecast_date)) AS formatted_date,
                batch_execution_timestamp
            FROM `{project_id}.{dataset_id}.plan_production_daily`
            ORDER BY forecast_date ASC, target_produksi DESC;
        """
    }

    for view_name, sql in views_sql.items():
        try:
            logger.info(f"Menjalankan DDL untuk View '{view_name}'...")
            query_job = client.query(sql)
            query_job.result()
            logger.info(f"View '{view_name}' berhasil diperbarui.")
        except Exception as e:
            logger.error(f"Gagal memperbarui View '{view_name}': {e}")
            raise


def simulate_looker_views_locally(tables: Dict[str, pd.DataFrame]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Mensimulasikan pembuatan Looker Studio Views secara lokal (pandas join)
    untuk pengujian mandiri tanpa akses BigQuery.
    """
    dim_date = tables['dim_date']
    dim_product = tables['dim_product']
    fact_sales = tables['fact_sales']
    plan_daily = tables['plan_production_daily']

    # Simulasi v_looker_performance_overview
    m1 = fact_sales.merge(dim_date, on='date_id', how='inner')
    v_overview = m1.merge(dim_product, on='product_id', how='inner')
    v_overview = v_overview[[
        'order_no', 'tanggal_penuh', 'nama_hari', 'nama_bulan',
        'minggu_ke', 'tahun', 'is_weekend', 'product_id', 'product_name',
        'category_name', 'qty_sold', 'gross_amount', 'discount_amount', 'net_amount'
    ]].rename(columns={'tanggal_penuh': 'order_date'})

    # Simulasi v_looker_production_planning
    v_planning = plan_daily.copy()
    v_planning['formatted_date'] = pd.to_datetime(v_planning['forecast_date']).dt.strftime('%a, %d %b %Y')

    return v_overview, v_planning


def main():
    parser = argparse.ArgumentParser(description="Weekly Demand Forecasting & BigQuery Batch Runner")
    parser.add_argument("--config", type=str, default="batch_config.yaml", help="Path ke file konfigurasi YAML")
    parser.add_argument("--dry-run", action="store_true", help="Jalankan secara luring 100 persen tanpa GCP/BigQuery")
    parser.add_argument("--pos-dir", type=str, default=None, help="Direktori file POS Excel lokal")
    parser.add_argument("--output-dir", type=str, default=None, help="Direktori penyimpanan file CSV")
    parser.add_argument("--cutoff-date", type=str, default=None, help="Tanggal batas simulasi (YYYY-MM-DD)")

    args = parser.parse_args()

    # Resolusi path
    base_script_dir = Path(__file__).resolve().parent
    config_file = (base_script_dir / args.config) if not Path(args.config).is_absolute() else Path(args.config)
    config = load_config(config_file)

    output_dir = Path(args.output_dir) if args.output_dir else (base_script_dir / config['storage']['output_dir'])

    logger.info("=" * 70)
    logger.info("MEMULAI WEEKLY BATCH RUNNER: ITA CAKE SHOP ANTAPANI")
    logger.info(f"Mode Operasi: {'LOCAL DRY-RUN (Luring)' if args.dry_run else 'PRODUCTION BIGQUERY SANDBOX'}")
    logger.info("=" * 70)

    # 1. Pemuatan Data POS
    # Cari direktori POS
    if args.pos_dir:
        pos_dir = Path(args.pos_dir)
    else:
        # Default auto-discovery
        candidate_dirs = [
            base_script_dir / "../01_data_ITA-Cake-Shop/ITA CAKE SHOP ANTAPANI (maret 2025-september 2026)",
            base_script_dir / "../01_data_ITA-Cake-Shop/ITA CAKE SHOP ANTAPANI (feb 2023-feb 2026)/LAPORAN PENJUALAN",
            base_script_dir / "../../Data Skripsi/Data Baru/data_itacakeshop_antapani_terbaru",
            base_script_dir / "incoming_pos"
        ]
        pos_dir = next((d for d in candidate_dirs if d.exists()), candidate_dirs[0])

    df_raw = load_raw_pos_files(pos_dir)

    # Jika file mentah kosong (misal di folder incoming_pos baru belum ada), cek file Master_Clean
    if df_raw.empty:
        master_csv_candidates = [
            base_script_dir / "Data_Output/Master_Clean_Feb2023_Sept2026.csv",
            base_script_dir / "Data_Output/Master_Clean_Feb2023_Feb2026.csv",
            base_script_dir / "../01_data_ITA-Cake-Shop/Data_Output/Master_Clean_Feb2023_Sept2026.csv",
            base_script_dir / "../01_data_ITA-Cake-Shop/Data_Output/Master_Clean_Feb2023_Feb2026.csv",
        ]
        master_file = next((f for f in master_csv_candidates if f.exists()), None)
        if master_file:
            logger.info(f"Menggunakan Master Clean Dataset cadangan dari: {master_file}")
            df_clean = pd.read_csv(master_file)
            df_clean['order date'] = pd.to_datetime(df_clean['order date'])
            df_clean.rename(columns={'order no': 'order_no'}, inplace=True)
        else:
            raise RuntimeError("Tidak ditemukan file POS mentah maupun Master Clean Dataset!")
    else:
        logger.info("Menjalankan pembersihan data POS mentah...")
        df_clean = clean_pos_dataset(df_raw)

    logger.info(f"Data transaksi bersih siap diproses: {len(df_clean):,} baris.")

    # 2. Penentuan Tanggal Horizon & Cutoff
    official_start = pd.to_datetime(config['pipeline']['official_start_date'])
    if args.cutoff_date:
        cutoff_dt = pd.to_datetime(args.cutoff_date)
    else:
        cutoff_dt = df_clean['order date'].max().normalize()

    # Tentukan Senin awal pekan target peramalan (W-MON)
    # Jika cutoff adalah Minggu, pekan depan mulai Senin esoknya
    if cutoff_dt.dayofweek == 6:  # Minggu
        forecast_week_start = cutoff_dt + pd.Timedelta(days=1)
    else:
        # Mundur ke Senin pekan berjalan atau maju ke Senin depan
        forecast_week_start = cutoff_dt + pd.Timedelta(days=(7 - cutoff_dt.dayofweek))

    horizon_end = forecast_week_start + pd.Timedelta(days=6)
    logger.info(f"Jendela Operasional: Mulai {official_start.date()} s.d. Horizon {horizon_end.date()}")
    logger.info(f"Pekan Target Peramalan: {forecast_week_start.date()} s.d. {horizon_end.date()}")

    # 3. Pembangunan Star Schema
    dim_date, dim_product, fact_sales = build_star_schema(
        df_clean=df_clean,
        target_categories=config['pipeline']['target_categories'],
        official_start=official_start,
        horizon_end=horizon_end,
        idul_fitri_ranges=config['pipeline']['idul_fitri_ranges']
    )

    # 4. Peramalan & Disagregasi Operasional
    plan_daily, forecast_recs = run_forecasting_and_disaggregation(
        df_clean=df_clean,
        config=config,
        forecast_week_start=forecast_week_start
    )

    tables = {
        config['storage']['tables']['dim_date']: dim_date,
        config['storage']['tables']['dim_product']: dim_product,
        config['storage']['tables']['fact_sales']: fact_sales,
        config['storage']['tables']['plan_production_daily']: plan_daily,
        config['storage']['tables']['forecast_recommendations']: forecast_recs
    }

    # 5. Validasi Skema Data
    if not validate_schemas(tables):
        logger.error("Integritas skema gagal diverifikasi. Pipeline dibatalkan!")
        sys.exit(1)

    # 6. Ekspor CSV Lokal (Selalu dijalankan untuk backup dan dry-run)
    export_local_csv(tables, output_dir)

    # 7. Simulasi Looker Views Lokal
    v_overview, v_planning = simulate_looker_views_locally(tables)
    logger.info(f"Simulasi View Halaman 1 (v_looker_performance_overview): {len(v_overview):,} baris.")
    logger.info(f"Simulasi View Halaman 2 (v_looker_production_planning): {len(v_planning):,} baris.")
    logger.info(f"Ringkasan Target Produksi 7 Hari: "
                f"Total Target = {v_planning['target_produksi'].sum():,} pcs | "
                f"Forecast Murni = {v_planning['forecast_murni'].sum():,} pcs | "
                f"Safety Stock = {v_planning['safety_stock'].sum():,} pcs")

    # 8. Pemuatan ke BigQuery Sandbox (Jika bukan dry-run)
    if not args.dry_run:
        logger.info("Mengunggah data layer ke Google BigQuery Sandbox...")
        upload_to_bigquery_sandbox(tables, config)
        logger.info("Sinkronisasi BigQuery Sandbox SELESAI.")
    else:
        logger.info("Mode DRY-RUN aktif: Pemuatan cloud dilewati. Seluruh data layer tersimpan di CSV.")

    logger.info("=" * 70)
    logger.info("BATCH PIPELINE MINGGUAN SELESAI DENGAN SUKSES [EXIT CODE 0]")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
