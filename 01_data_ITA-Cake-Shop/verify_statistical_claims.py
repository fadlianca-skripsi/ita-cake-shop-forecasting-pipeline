import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from statsmodels.tsa.stattools import adfuller, acf
from statsmodels.tsa.seasonal import seasonal_decompose

# Define paths
BASE_DIR = Path(r"c:\Users\admin\Documents\Semester 8 & 9\Skripsi(2)\FINAL_BERSIH\01_data_ITA-Cake-Shop")
DATA_DIR = BASE_DIR / "Data_Output"
MASTER_CSV = DATA_DIR / "Master_Clean_Feb2023_Feb2026.csv"
WEEKLY_CSV = DATA_DIR / "weekly_clean_final.csv"

print(f"Loading master CSV from: {MASTER_CSV}")
df_skripsi = pd.read_csv(MASTER_CSV, parse_dates=['order date'])
print(f"Master CSV shape: {df_skripsi.shape}")

print(f"Loading weekly CSV from: {WEEKLY_CSV}")
weekly_clean = pd.read_csv(WEEKLY_CSV, parse_dates=['date'], index_col='date')
print(f"Weekly CSV shape: {weekly_clean.shape}")
print(f"Weekly index range: {weekly_clean.index.min()} to {weekly_clean.index.max()}, count: {len(weekly_clean)}")

target_cats = ['Cake', 'Japanese', 'Mille Crepes']

print("\n" + "="*80)
print("TEST 1: SPARSITY & ZERO-SALES CALCULATION")
print("="*80)

df_target = df_skripsi[df_skripsi['item group'].isin(target_cats)].copy()
min_date = df_target['order date'].min()
max_date = df_target['order date'].max()
total_days = (max_date - min_date).days + 1
unique_skus = df_target['item name'].unique()
num_skus = len(unique_skus)

print(f"Target categories: {target_cats}")
print(f"Date range: {min_date.date()} to {max_date.date()} -> Total days: {total_days}")
print(f"Unique target SKUs count: {num_skus}")
print(f"Expected grid size (days * skus): {total_days} * {num_skus} = {total_days * num_skus}")

dates = pd.date_range(min_date, max_date, freq='D')
full_idx = pd.MultiIndex.from_product([dates, unique_skus], names=['order date', 'item name'])
daily_grid = df_target.groupby(['order date', 'item name'])['qty'].sum().reindex(full_idx, fill_value=0).reset_index()

total_sku_days = len(daily_grid)
zero_sku_days = (daily_grid['qty'] == 0).sum()
active_sku_days = (daily_grid['qty'] > 0).sum()
sparsity_sku_pct = (zero_sku_days / total_sku_days) * 100

print(f"Total grid rows: {total_sku_days:,}")
print(f"Zero SKU-days: {zero_sku_days:,}")
print(f"Active SKU-days: {active_sku_days:,}")
print(f"Daily SKU Sparsity: {sparsity_sku_pct:.4f}% ({sparsity_sku_pct:.2f}%)")

# Compare with notebook claims
nb_total_sku_days = 94482
nb_zero_sku_days = 80642
nb_sparsity_pct = 85.35

print(f"Notebook claim: {nb_zero_sku_days} zero days out of {nb_total_sku_days} combinations -> {nb_sparsity_pct}%")
diff_total = total_sku_days - nb_total_sku_days
diff_zero = zero_sku_days - nb_zero_sku_days
print(f"Discrepancy: Total diff = {diff_total}, Zero diff = {diff_zero}, Sparsity diff = {sparsity_sku_pct - nb_sparsity_pct:.4f}%")

# Weekly category sparsity
print("\nWeekly Category Sparsity (from weekly_clean_final.csv):")
for cat in target_cats:
    zero_weeks = (weekly_clean[cat] == 0).sum()
    total_weeks = len(weekly_clean)
    wk_sparsity = (zero_weeks / total_weeks) * 100
    print(f"  - {cat:<12}: {zero_weeks}/{total_weeks} weeks = {wk_sparsity:.4f}% ({wk_sparsity:.2f}%)")

# Top 5 Zero-Sales and Top 5 Active SKUs
sku_zero_stats = daily_grid.groupby('item name').agg(
    total_days=('qty', 'count'),
    zero_days=('qty', lambda x: (x == 0).sum()),
    total_qty=('qty', 'sum')
)
sku_zero_stats['zero_pct'] = (sku_zero_stats['zero_days'] / sku_zero_stats['total_days']) * 100

print("\nTop 5 Zero-Sales SKUs:")
top5_zero = sku_zero_stats.sort_values('zero_pct', ascending=False).head(5)
for sku, row in top5_zero.iterrows():
    print(f"  {sku:<35}: {row['zero_days']:.0f}/{row['total_days']:.0f} zero days ({row['zero_pct']:.2f}%), Total Qty: {row['total_qty']:.0f}")

print("\nTop 5 Active SKUs:")
top5_active = sku_zero_stats.sort_values('zero_pct', ascending=True).head(5)
for sku, row in top5_active.iterrows():
    print(f"  {sku:<35}: {row['zero_days']:.0f}/{row['total_days']:.0f} zero days ({row['zero_pct']:.2f}%), Total Qty: {row['total_qty']:.0f}")

print("\n" + "="*80)
print("TEST 2: COEFFICIENT OF VARIATION (CV) & DEMAND PROFILE CLASSIFICATION")
print("="*80)

print("Category Level Weekly CV (weekly_clean_final.csv):")
weekly_cv_data = []
for cat in target_cats:
    s = weekly_clean[cat]
    m = s.mean()
    sd = s.std(ddof=1)
    sd_pop = s.std(ddof=0)
    cv = sd / m
    cv2 = cv ** 2
    print(f"  {cat:<12}: Mean = {m:.2f}, Std(ddof=1) = {sd:.2f}, Std(ddof=0) = {sd_pop:.2f}, CV = {cv:.4f}, CV^2 = {cv2:.4f}, CV^2 < 0.49: {cv2 < 0.49}")

print("\nSKU Level Demand Profile (Syntetos-Boylan / Kostenko):")
# Compute ADI (Average Demand Interval = total periods / non-zero periods) and CV^2 on non-zero demands
sku_classification = []
for sku in unique_skus:
    sku_daily = daily_grid[daily_grid['item name'] == sku].sort_values('order date')
    total_periods = len(sku_daily)
    non_zero = sku_daily[sku_daily['qty'] > 0]['qty']
    num_non_zero = len(non_zero)
    if num_non_zero == 0:
        continue
    adi = total_periods / num_non_zero
    cv_nonzero = non_zero.std(ddof=1) / non_zero.mean() if num_non_zero > 1 else 0
    cv2_nonzero = cv_nonzero ** 2
    # Full series CV (including zeros)
    cv_full = sku_daily['qty'].std(ddof=1) / sku_daily['qty'].mean()
    cv2_full = cv_full ** 2
    
    # Syntetos-Boylan cutoff: ADI cutoff = 1.32, CV^2 cutoff = 0.49
    if adi < 1.32 and cv2_nonzero < 0.49:
        cat_sb = "Smooth"
    elif adi >= 1.32 and cv2_nonzero < 0.49:
        cat_sb = "Intermittent"
    elif adi < 1.32 and cv2_nonzero >= 0.49:
        cat_sb = "Erratic"
    else:
        cat_sb = "Lumpy"
        
    sku_classification.append({
        'sku': sku,
        'adi': adi,
        'cv2_nonzero': cv2_nonzero,
        'cv2_full': cv2_full,
        'category_sb': cat_sb
    })

df_sku_class = pd.DataFrame(sku_classification)
print(f"Total classified SKUs: {len(df_sku_class)}")
print("SKU Demand Category Distribution (Syntetos-Boylan):")
print(df_sku_class['category_sb'].value_counts())
print(f"SKUs with CV^2 (full series including zeros) >= 0.49: {(df_sku_class['cv2_full'] >= 0.49).sum()} / {len(df_sku_class)} ({(df_sku_class['cv2_full'] >= 0.49).mean()*100:.1f}%)")
print(f"Mean SKU CV^2 (full): {df_sku_class['cv2_full'].mean():.2f}, Median: {df_sku_class['cv2_full'].median():.2f}")

print("\n" + "="*80)
print("TEST 3: MEAN VS STD CORRELATION (MULTIPLICATIVE PROOF & HOMOSCEDASTICITY REFUTATION)")
print("="*80)

# Apply Idul Fitri masking & IQR capping as done in notebook
IDUL_FITRI_WINDOWS = [
    (pd.Timestamp('2023-04-08'), pd.Timestamp('2023-04-25')),
    (pd.Timestamp('2024-03-27'), pd.Timestamp('2024-04-13')),
    (pd.Timestamp('2025-03-17'), pd.Timestamp('2025-04-03')),
]

cleaned_weekly = weekly_clean.copy()
for start_dt, end_dt in IDUL_FITRI_WINDOWS:
    mask = (cleaned_weekly.index + pd.Timedelta(days=6) >= start_dt) & (cleaned_weekly.index <= end_dt)
    cleaned_weekly.loc[mask, :] = np.nan

cleaned_weekly = cleaned_weekly.interpolate(method='linear').bfill().ffill()

for cat in target_cats:
    q1 = cleaned_weekly[cat].quantile(0.25)
    q3 = cleaned_weekly[cat].quantile(0.75)
    iqr = q3 - q1
    upper_fence = q3 + 1.5 * iqr
    cleaned_weekly[cat] = np.where(cleaned_weekly[cat] > upper_fence, upper_fence, cleaned_weekly[cat])

print("3A. Correlation on Cleaned Series (as in notebook):")
for cat in target_cats:
    s = cleaned_weekly[cat]
    m_blocks = s.groupby(pd.Grouper(freq='ME' if hasattr(pd.Grouper(freq='ME'), 'freq') else 'M')).agg(['mean', 'std']).dropna()
    r, p = pearsonr(m_blocks['mean'], m_blocks['std'])
    print(f"  {cat:<12}: N months = {len(m_blocks)}, Pearson r = {r:.4f}, p-value = {p:.4e}, p < 0.05: {p < 0.05}")

print("\n3B. Correlation on Raw Series (before masking & capping):")
for cat in target_cats:
    s = weekly_clean[cat]
    m_blocks_raw = s.groupby(pd.Grouper(freq='ME' if hasattr(pd.Grouper(freq='ME'), 'freq') else 'M')).agg(['mean', 'std']).dropna()
    r_raw, p_raw = pearsonr(m_blocks_raw['mean'], m_blocks_raw['std'])
    print(f"  {cat:<12}: N months = {len(m_blocks_raw)}, Pearson r = {r_raw:.4f}, p-value = {p_raw:.4e}, p < 0.05: {p_raw < 0.05}")

print("\n3C. Robustness: Rolling Window Mean vs Std Correlation (Cleaned Series):")
for w in [4, 8, 12]:
    print(f"  --- Rolling Window = {w} weeks ---")
    for cat in target_cats:
        r_mean = cleaned_weekly[cat].rolling(w).mean().dropna()
        r_std = cleaned_weekly[cat].rolling(w).std().dropna()
        common_idx = r_mean.index.intersection(r_std.index)
        r_val, p_val = pearsonr(r_mean.loc[common_idx], r_std.loc[common_idx])
        print(f"    {cat:<12}: r = {r_val:.4f}, p = {p_val:.4e}, p < 0.05: {p_val < 0.05}")

print("\n" + "="*80)
print("TEST 4: SEASONAL DECOMPOSITION (m = 26, model='multiplicative')")
print("="*80)

for cat in target_cats:
    series = cleaned_weekly[cat].dropna().replace(0, 0.1)
    zero_count = (series == 0).sum()
    min_val = series.min()
    print(f"\nCategory: {cat} (N = {len(series)}, min = {min_val:.2f}, zero_count = {zero_count})")
    
    decomp = seasonal_decompose(series, model='multiplicative', period=26)
    
    s_factors = decomp.seasonal
    trend = decomp.trend
    resid = decomp.resid
    
    nan_seasonal = s_factors.isna().sum()
    nan_trend = trend.isna().sum()
    nan_resid = resid.isna().sum()
    
    print(f"  Seasonal component: length = {len(s_factors)}, NaNs = {nan_seasonal}, min = {s_factors.min():.4f}, max = {s_factors.max():.4f}, mean = {s_factors.mean():.4f}")
    print(f"  Trend component: length = {len(trend)}, NaNs = {nan_trend} (Expected 26 edge NaNs: 13 start + 13 end)")
    print(f"  Resid component: length = {len(resid)}, NaNs = {nan_resid}")
    
    # Check periodicity of seasonal component
    unique_season_factors = s_factors.iloc[:26].values
    repeated_season_factors = s_factors.iloc[26:52].values
    is_periodic = np.allclose(unique_season_factors, repeated_season_factors)
    print(f"  Seasonal factor periodicity exact match (first 26 vs second 26): {is_periodic}")
    print(f"  Mean of 26 seasonal factors: {np.mean(unique_season_factors):.4f} (Ideal multiplicative = 1.0000)")
    print(f"  Seasonal factors strictly positive: {(s_factors > 0).all()}")

print("\n" + "="*80)
print("TEST 5: AUTOCORRELATION FUNCTION (ACF) AT LAGS 7, 12, 26")
print("="*80)

for cat in target_cats:
    vals, confint = acf(cleaned_weekly[cat], nlags=52, alpha=0.05)
    print(f"\nCategory: {cat} (Cleaned Series):")
    for lag in [7, 12, 26]:
        r_lag = vals[lag]
        ci_lower = confint[lag, 0] - vals[lag]
        ci_upper = confint[lag, 1] - vals[lag]
        # Bartlett significance: is r_lag outside [-1.96/sqrt(N), 1.96/sqrt(N)]?
        # Note: confint in statsmodels is the 95% CI around the ACF estimate (or around 0 depending on method)
        # Statsmodels confint[:, 0] and confint[:, 1] are lower and upper bounds of the ACF value
        # A lag is significantly different from 0 if 0 is not inside [confint[lag, 0], confint[lag, 1]]
        sig_diff_zero = not (confint[lag, 0] <= 0 <= confint[lag, 1])
        print(f"  Lag {lag:>2}: ACF = {r_lag:>7.4f}, 95% CI = [{confint[lag, 0]:>7.4f}, {confint[lag, 1]:>7.4f}], Sig != 0: {sig_diff_zero}")

print("\nComparison with Raw Series ACF:")
for cat in target_cats:
    vals_raw, confint_raw = acf(weekly_clean[cat], nlags=52, alpha=0.05)
    print(f"  {cat:<12}: Lag 7 = {vals_raw[7]:.4f}, Lag 12 = {vals_raw[12]:.4f}, Lag 26 = {vals_raw[26]:.4f}")
