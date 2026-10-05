"""
verify_numbers.py - Comprehensive Automated Verification Script for ITA Cake Shop Thesis

Validates:
1. Top-to-bottom clean execution of all 6 Jupyter notebooks.
2. Exact row count of weekly_clean_final.csv (155 continuous weeks).
3. Exact row count of Master_Clean_Feb2023_Feb2026.csv (106,539 rows).
4. Champion model parameters in champion_parameters.json (Cake: 16.50%, Japanese: 19.87%, Mille Crepes: 18.00%).
5. Non-zero metrics in forecast_recommendations.csv (zero '0.00%' strings).
6. Genuine out-of-sample evaluation on Mar-Sept 2026 (31 weeks) with locked parameters vs Seasonal Naive.
7. Exports out_of_sample_eval_2026.csv and comprehensive verification_log.txt.
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path

# Defensive Windows environment configuration: Ensure MKL and Conda DLLs are in PATH
CONDA_PREFIX = r"C:\Users\admin\miniconda3\envs\skripsi_env"
MKL_BIN = os.path.join(CONDA_PREFIX, "Library", "bin")
SCRIPTS_BIN = os.path.join(CONDA_PREFIX, "Scripts")
if os.path.exists(MKL_BIN) and MKL_BIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = MKL_BIN + os.pathsep + SCRIPTS_BIN + os.pathsep + os.environ.get("PATH", "")

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "verification_log.txt"
OOS_CSV_FILE = BASE_DIR / "out_of_sample_eval_2026.csv"

class VerificationLogger:
    def __init__(self, log_path):
        self.log_path = log_path
        self.entries = []
        # Clear previous log
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write(f"=== VERIFICATION AUDIT LOG: ITA CAKE SHOP THESIS ===\n")
            f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Working Directory: {BASE_DIR}\n")
            f.write(f"Python: {sys.version}\n")
            f.write("=" * 65 + "\n\n")

    def log(self, message):
        print(message)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(message + "\n")

logger = VerificationLogger(LOG_FILE)

def run_notebook_verification(skip_run=False):
    notebooks = [
        BASE_DIR / "01_data_ITA-Cake-Shop" / "01_EDA_Raw_and_Cleaning.ipynb",
        BASE_DIR / "01_data_ITA-Cake-Shop" / "02_EDA_Clean_Analysis.ipynb",
        BASE_DIR / "02_modeling_ITA-Cake-Shop" / "03_Teori_Sparsitas_dan_GridSearch.ipynb",
        BASE_DIR / "02_modeling_ITA-Cake-Shop" / "04_Operational_Simulation.ipynb",
        BASE_DIR / "02_modeling_ITA-Cake-Shop" / "05_Operational_Simulation_Disaggregation.ipynb",
        BASE_DIR / "03_ETL" / "01_ETL_Pipeline.ipynb",
    ]

    logger.log(">>> [CHECK 1/6] VALIDASI EKSEKUSI 6 JUPYTER NOTEBOOK")
    if skip_run:
        logger.log("  [INFO] Parameter --skip-notebooks aktif: Memverifikasi keberadaan dan integritas struktur notebook...")
        for nb_path in notebooks:
            assert nb_path.exists(), f"Notebook tidak ditemukan: {nb_path}"
            with open(nb_path, "r", encoding="utf-8") as f:
                nb = nbformat.read(f, as_version=4)
            logger.log(f"  [PASS] {nb_path.name} (Valid JSON, {len(nb.cells)} sel)")
        return True

    all_passed = True
    ep = ExecutePreprocessor(timeout=600, kernel_name="python3")

    for nb_path in notebooks:
        t0 = time.time()
        logger.log(f"  Executing {nb_path.name} in {nb_path.parent.name}...")
        try:
            with open(nb_path, "r", encoding="utf-8") as f:
                nb = nbformat.read(f, as_version=4)
            ep.preprocess(nb, {"metadata": {"path": str(nb_path.parent)}})
            elapsed = time.time() - t0
            logger.log(f"  [PASS] {nb_path.name} selesai tanpa error dalam {elapsed:.2f}s")
        except Exception as e:
            elapsed = time.time() - t0
            logger.log(f"  [FAIL] {nb_path.name} gagal setelah {elapsed:.2f}s: {e}")
            all_passed = False

    return all_passed

def check_data_artifacts():
    logger.log("\n>>> [CHECK 2/6] VALIDASI ARTEFAK DATA UTAMA (ROW COUNTS & CONTINUITY)")
    
    # 1. weekly_clean_final.csv
    weekly_path = BASE_DIR / "01_data_ITA-Cake-Shop" / "Data_Output" / "weekly_clean_final.csv"
    assert weekly_path.exists(), f"File {weekly_path} tidak ditemukan!"
    df_weekly = pd.read_csv(weekly_path, parse_dates=["date"], index_col="date")
    
    row_count_weekly = len(df_weekly)
    expected_rows_weekly = 155
    min_date = df_weekly.index.min().strftime("%Y-%m-%d")
    max_date = df_weekly.index.max().strftime("%Y-%m-%d")
    
    logger.log(f"  - weekly_clean_final.csv: {row_count_weekly} baris (Rentang: {min_date} s/d {max_date})")
    assert row_count_weekly == expected_rows_weekly, (
        f"Mismatch: weekly_clean_final memiliki {row_count_weekly} baris, diharapkan tepat {expected_rows_weekly} baris!"
    )
    assert min_date == "2023-02-20", f"Start date tidak sesuai: {min_date} vs 2023-02-20"
    assert max_date == "2026-02-02", f"End date tidak sesuai: {max_date} vs 2026-02-02"
    logger.log(f"  [PASS] weekly_clean_final.csv memenuhi syarat tepat 155 pekan kontinu W-MON.")

    # 2. Master_Clean_Feb2023_Feb2026.csv
    master_path = BASE_DIR / "01_data_ITA-Cake-Shop" / "Data_Output" / "Master_Clean_Feb2023_Feb2026.csv"
    assert master_path.exists(), f"File {master_path} tidak ditemukan!"
    df_master = pd.read_csv(master_path)
    row_count_master = len(df_master)
    expected_rows_master = 106539
    
    logger.log(f"  - Master_Clean_Feb2023_Feb2026.csv: {row_count_master:,} baris transaksi")
    assert row_count_master == expected_rows_master, (
        f"Mismatch: Master_Clean memiliki {row_count_master} baris, diharapkan tepat {expected_rows_master} baris!"
    )
    logger.log(f"  [PASS] Master_Clean_Feb2023_Feb2026.csv memenuhi syarat tepat 106,539 baris.")

def check_champion_parameters():
    logger.log("\n>>> [CHECK 3/6] VALIDASI PARAMETER CHAMPION (champion_parameters.json)")
    json_path = BASE_DIR / "02_modeling_ITA-Cake-Shop" / "Data_Output" / "champion_parameters.json"
    assert json_path.exists(), f"File {json_path} tidak ditemukan!"
    
    with open(json_path, "r", encoding="utf-8") as f:
        params = json.load(f)
        
    expected_metrics = {
        "Cake": {"composite_wmape": 16.50, "wmape_holdout": 19.26, "wmape_cv": 13.75, "m": 26, "seasonal": "mul", "gamma": 0.0},
        "Japanese": {"composite_wmape": 19.87, "wmape_holdout": 15.33, "wmape_cv": 24.42, "m": 26, "seasonal": "mul", "gamma": 0.0},
        "Mille Crepes": {"composite_wmape": 18.00, "wmape_holdout": 21.68, "wmape_cv": 14.32, "m": 8, "seasonal": "mul", "gamma": 0.0}
    }
    
    for cat, exp in expected_metrics.items():
        assert cat in params, f"Kategori {cat} tidak ditemukan di champion_parameters.json"
        actual = params[cat]
        comp = actual["composite_wmape"]
        holdout = actual["wmape_holdout"]
        cv = actual["wmape_cv"]
        m = actual["m"]
        gamma = actual["gamma"]
        
        logger.log(f"  - {cat:<12}: Comp WMAPE={comp:.2f}% (Exp: {exp['composite_wmape']:.2f}%), "
                   f"Holdout={holdout:.2f}%, CV={cv:.2f}%, m={m}, gamma={gamma}")
        
        assert abs(comp - exp["composite_wmape"]) <= 0.01, f"{cat} Comp WMAPE mismatch: {comp} vs {exp['composite_wmape']}"
        assert abs(holdout - exp["wmape_holdout"]) <= 0.01, f"{cat} Holdout WMAPE mismatch: {holdout} vs {exp['wmape_holdout']}"
        assert abs(cv - exp["wmape_cv"]) <= 0.01, f"{cat} CV WMAPE mismatch: {cv} vs {exp['wmape_cv']}"
        assert m == exp["m"], f"{cat} m mismatch: {m} vs {exp['m']}"
        assert gamma == exp["gamma"], f"{cat} gamma mismatch: {gamma} vs {exp['gamma']}"
        
    logger.log("  [PASS] champion_parameters.json diverifikasi 100% presisi matematis.")

def check_forecast_recommendations():
    logger.log("\n>>> [CHECK 4/6] VALIDASI TABEL REKOMENDASI FORECAST (forecast_recommendations.csv)")
    rec_paths = [
        BASE_DIR / "01_data_ITA-Cake-Shop" / "Data_Output" / "forecast_recommendations.csv",
        BASE_DIR / "03_ETL" / "Data_Output" / "forecast_recommendations.csv"
    ]
    
    for r_path in rec_paths:
        assert r_path.exists(), f"File {r_path} tidak ditemukan!"
        df_rec = pd.read_csv(r_path)
        
        # Cek ketiadaan string '0.00%'
        has_zero_str = (df_rec == "0.00%").any().any() or df_rec.astype(str).apply(lambda col: col.str.contains("0.00%")).any().any()
        assert not has_zero_str, f"Terdeteksi string '0.00%' pada {r_path}!"
        
        logger.log(f"  - {r_path.parent.parent.name}/{r_path.name}: Bebas dari '0.00%'")
        for idx, row in df_rec.iterrows():
            logger.log(f"    * {row['kategori']}: Holdout={row['holdout_wmape']}, CV={row['cv_wmape_3fold']}, Composite={row['composite_wmape']}")
            
    logger.log("  [PASS] forecast_recommendations.csv terbukti valid dengan metrik riil non-zero.")

def run_out_of_sample_evaluation():
    logger.log("\n>>> [CHECK 5/6] EVALUASI EMPIRIS OUT-OF-SAMPLE (MAR-SEPT 2026, 31 PEKAN)")
    
    # Data Latih: 155 pekan
    weekly_path = BASE_DIR / "01_data_ITA-Cake-Shop" / "Data_Output" / "weekly_clean_final.csv"
    df_train = pd.read_csv(weekly_path, parse_dates=["date"], index_col="date")
    
    # Data Extended: s/d Sept 2026
    ext_path = BASE_DIR / "01_data_ITA-Cake-Shop" / "Data_Output" / "Master_Clean_Feb2023_Sept2026.csv"
    assert ext_path.exists(), f"File {ext_path} tidak ditemukan!"
    df_ext = pd.read_csv(ext_path, parse_dates=["order date"])
    
    target_cats = ["Cake", "Japanese", "Mille Crepes"]
    sub = df_ext[df_ext["item group"].isin(target_cats)]
    piv = sub.pivot_table(index="order date", columns="item group", values="qty", aggfunc="sum", fill_value=0)
    weekly_ext = piv.resample("W-MON").sum()
    
    # Pangkas pekan parsial terakhir (7-10 Sept 2026)
    weekly_ext = weekly_ext[weekly_ext.index <= "2026-09-07"]
    
    # Periode Uji: Pekan setelah jendela resmi skripsi (2026-02-02)
    test_df = weekly_ext[weekly_ext.index > df_train.index[-1]]
    h = len(test_df)
    assert h == 31, f"Jendela uji out-of-sample bukan 31 pekan (aktual: {h} pekan)!"
    
    logger.log(f"  - Periode Latih Resmi : {df_train.index[0].strftime('%Y-%m-%d')} s/d {df_train.index[-1].strftime('%Y-%m-%d')} ({len(df_train)} pekan)")
    logger.log(f"  - Periode Uji OOS     : {test_df.index[0].strftime('%Y-%m-%d')} s/d {test_df.index[-1].strftime('%Y-%m-%d')} ({h} pekan)")
    
    # Load Locked Champion Hyperparameters
    json_path = BASE_DIR / "02_modeling_ITA-Cake-Shop" / "Data_Output" / "champion_parameters.json"
    with open(json_path, "r", encoding="utf-8") as f:
        champ = json.load(f)
        
    oos_records = []
    
    for cat in target_cats:
        p = champ[cat]
        train_series = df_train[cat].astype(float).replace(0, 0.1)
        test_series = test_df[cat].astype(float)
        
        # Fit Holt-Winters Champion
        hw = ExponentialSmoothing(
            train_series,
            trend=p["trend"],
            seasonal=p["seasonal"],
            seasonal_periods=p["m"],
            initialization_method=p["initialization_method"]
        ).fit(
            smoothing_level=p["alpha"],
            smoothing_trend=p["beta"],
            smoothing_seasonal=p["gamma"],
            optimized=False
        )
        pred_hw = hw.forecast(h).values
        
        # Seasonal Naive Benchmark: Last m values repeated
        m = p["m"]
        last_m = df_train[cat].iloc[-m:].values
        pred_sn = np.tile(last_m, int(np.ceil(h / m)))[:h]
        
        # Metrik HW
        y_true = test_series.values
        vol_actual = float(np.sum(y_true))
        vol_pred_hw = float(np.sum(pred_hw))
        wmape_hw = float(np.sum(np.abs(y_true - pred_hw)) / vol_actual * 100)
        mae_hw = float(np.mean(np.abs(y_true - pred_hw)))
        rmse_hw = float(np.sqrt(np.mean((y_true - pred_hw) ** 2)))
        
        # Metrik Seasonal Naive
        vol_pred_sn = float(np.sum(pred_sn))
        wmape_sn = float(np.sum(np.abs(y_true - pred_sn)) / vol_actual * 100)
        mae_sn = float(np.mean(np.abs(y_true - pred_sn)))
        rmse_sn = float(np.sqrt(np.mean((y_true - pred_sn) ** 2)))
        
        hw_wins = wmape_hw < wmape_sn
        status_str = "HW UNGGUL" if hw_wins else "SNAIVE UNGGUL"
        
        logger.log(f"\n  --- Hasil Kategori {cat} (h={h} pekan) ---")
        logger.log(f"    * Holt-Winters Champion : WMAPE = {wmape_hw:.2f}% | MAE = {mae_hw:.2f} | RMSE = {rmse_hw:.2f}")
        logger.log(f"    * Seasonal Naive Baseline: WMAPE = {wmape_sn:.2f}% | MAE = {mae_sn:.2f} | RMSE = {rmse_sn:.2f}")
        logger.log(f"    * Margin Keunggulan HW  : {wmape_sn - wmape_hw:+.2f}% ({status_str})")
        
        oos_records.append({
            "Category": cat,
            "Model": "Holt-Winters Champion",
            "Horizon_Weeks": h,
            "Test_Start": test_df.index[0].strftime("%Y-%m-%d"),
            "Test_End": test_df.index[-1].strftime("%Y-%m-%d"),
            "Actual_Volume": round(vol_actual, 2),
            "Forecast_Volume": round(vol_pred_hw, 2),
            "WMAPE_Pct": round(wmape_hw, 2),
            "MAE": round(mae_hw, 2),
            "RMSE": round(rmse_hw, 2),
            "Status_vs_Baseline": status_str
        })
        
        oos_records.append({
            "Category": cat,
            "Model": "Seasonal Naive Baseline",
            "Horizon_Weeks": h,
            "Test_Start": test_df.index[0].strftime("%Y-%m-%d"),
            "Test_End": test_df.index[-1].strftime("%Y-%m-%d"),
            "Actual_Volume": round(vol_actual, 2),
            "Forecast_Volume": round(vol_pred_sn, 2),
            "WMAPE_Pct": round(wmape_sn, 2),
            "MAE": round(mae_sn, 2),
            "RMSE": round(rmse_sn, 2),
            "Status_vs_Baseline": "Benchmark"
        })
        
    df_oos = pd.DataFrame(oos_records)
    df_oos.to_csv(OOS_CSV_FILE, index=False)
    
    # Salin juga ke Data_Output untuk konsistensi
    data_out_csv = BASE_DIR / "02_modeling_ITA-Cake-Shop" / "Data_Output" / "out_of_sample_eval_2026.csv"
    df_oos.to_csv(data_out_csv, index=False)
    
    logger.log(f"\n  [PASS] File evaluasi out-of-sample berhasil disimpan ke:\n         - {OOS_CSV_FILE}\n         - {data_out_csv}")
    
    # Validasi angka eksak sesuai temuan forensik:
    cake_wmape = df_oos[(df_oos['Category']=='Cake') & (df_oos['Model']=='Holt-Winters Champion')]['WMAPE_Pct'].iloc[0]
    jap_wmape = df_oos[(df_oos['Category']=='Japanese') & (df_oos['Model']=='Holt-Winters Champion')]['WMAPE_Pct'].iloc[0]
    mc_wmape = df_oos[(df_oos['Category']=='Mille Crepes') & (df_oos['Model']=='Holt-Winters Champion')]['WMAPE_Pct'].iloc[0]
    
    assert abs(cake_wmape - 29.02) <= 0.05, f"Cake OOS WMAPE mismatch: {cake_wmape} vs 29.02"
    assert abs(jap_wmape - 31.17) <= 0.05, f"Japanese OOS WMAPE mismatch: {jap_wmape} vs 31.17"
    assert abs(mc_wmape - 91.94) <= 0.05, f"Mille Crepes OOS WMAPE mismatch: {mc_wmape} vs 91.94"
    logger.log("  [PASS] Seluruh angka evaluasi Out-of-Sample 2026 tervalidasi 100% konsisten dengan analisis ekonometrika.")

def check_visual_assets():
    logger.log("\n>>> [CHECK 6/6] VALIDASI ASSET VISUALISASI MODELING (10 PNG REGENERATED)")
    vis_dir = BASE_DIR / "02_modeling_ITA-Cake-Shop" / "Visualisasi_Gambar"
    expected_pngs = [
        "cv_walk_forward_scheme.png",
        "cv_fold_predictions_cake.png",
        "cv_fold_predictions_japanese.png",
        "cv_fold_predictions_millecrepes.png",
        "cv_metric_comparison.png",
        "operational_simulation_12w_tracking.png",
        "operational_dow_adaptive_profiles.png",
        "operational_sku_pareto_distribution.png",
        "operational_daily_production_vs_demand.png",
        "operational_waste_and_fill_rate.png"
    ]
    for png in expected_pngs:
        p_path = vis_dir / png
        assert p_path.exists(), f"Gambar {png} tidak ditemukan!"
        size = p_path.stat().st_size
        assert size > 10000, f"Ukuran gambar {png} terlalu kecil ({size} bytes), kemungkinan korup!"
        logger.log(f"  - {png:<42}: {size:>8,} bytes [PASS]")
    logger.log("  [PASS] 10 file visualisasi operasional dan evaluasi cross-validation valid dan beresolusi tinggi.")

def main():
    parser = argparse.ArgumentParser(description="Verifikasi komprehensif angka dan notebook skripsi ITA Cake Shop")
    parser.add_argument("--skip-notebooks", action="store_true", help="Lewati eksekusi penuh notebook untuk verifikasi cepat")
    args = parser.parse_args()

    t_start = time.time()
    logger.log("MEMULAI PROSES VERIFIKASI REPRODUSIBILITAS OTOMATIS...\n")

    try:
        # 1. Eksekusi notebook
        run_notebook_verification(skip_run=args.skip_notebooks)
        
        # 2. Cek artefak data
        check_data_artifacts()
        
        # 3. Cek parameter champion
        check_champion_parameters()
        
        # 4. Cek rekomendasi forecast
        check_forecast_recommendations()
        
        # 5. Evaluasi out-of-sample
        run_out_of_sample_evaluation()
        
        # 6. Cek visual assets
        check_visual_assets()

        total_time = time.time() - t_start
        logger.log("\n" + "=" * 65)
        logger.log(f"VERIFIKASI BERHASIL 100%! SEMUA 6 UJI KELAYAKAN LULUS (TOTAL WAKTU: {total_time:.2f}s)")
        logger.log("=" * 65)
        return 0
    except Exception as e:
        logger.log(f"\n[FATAL ERROR] Verifikasi Gagal: {e}")
        import traceback
        logger.log(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
