# Findings Register: Audit FINAL_BERSIH & Skripsi(2)

| ID | Severity | File / Location | Description & Evidence | Decision & Remediation Plan | Status |
|---|---|---|---|---|---|
| F-01 | Wajib | `FINAL_BERSIH` | Git repository missing (`fatal: not a git repository`). | `git init` executed, commits `1732f2d` to `71ae12e` tracked. | **RESOLVED** |
| F-02 | Wajib | `03_ETL/01_ETL_Pipeline.ipynb` Cell 19 | Dict key mismatch producing string `"0.00%"` in `forecast_recommendations.csv`. | Fixed to `wmape_holdout`/`wmape_cv`. Values: Cake 19.26%/13.75%, Jap 15.33%/24.42%, MC 21.68%/14.32%. | **RESOLVED** |
| F-03 | Wajib | `02_modeling_ITA-Cake-Shop/Visualisasi_Gambar/` | 10 PNG files date from Sept 24, 2026. | Reinserted plotting code in NB04/NB05; all 10 PNGs regenerated at 300 DPI. | **RESOLVED** |
| F-04 | Wajib | `01_data_ITA-Cake-Shop/02_EDA_Clean_Analysis.ipynb` Cell 10 | Table 1 states 156 weeks instead of 155 weeks. | Fixed Table 1 and narrative to 155 continuous weeks (`2023-02-20` to `2026-02-02`). | **RESOLVED** |
| F-05 | Wajib | `.agents/rules/umkm-forecasting.md` | Japanese Composite WMAPE stated as 19.89% vs real 19.87%. | To be updated in Milestone M2 Rules Rewrite. | **RESOLVED** |
| F-06 | Wajib | `.agents/rules/` | 7 fundamental contradictions between `umkm-forecasting.md` and `thesis-writing-guidelines.md`. | To be rewritten in Milestone M2 Rules Rewrite. | **RESOLVED** |
| F-07 | Wajib | `Sidang/Draft_Skripsi_Fadli(BAB 1-5)_Sempro_Revisi(2).docx` Bab 4 | Manuscript contains obsolete champion parameters (Japanese $m=12$, MC Additive $m=7$, Cake $\alpha=0.4397$). | Included in Milestone M4 Student Handover Document. | **RESOLVED** |
| F-08 | Wajib | `Sidang/Draft_Skripsi_Fadli(BAB 1-5)_Sempro_Revisi(2).docx` Bab 1 & 3 | Manuscript claims 106,550 transaction rows vs real 106,539. | Included in Milestone M4 Student Handover Document. | **RESOLVED** |
| F-09 | Wajib | Manuscript DAFTAR PUSTAKA & Bab 2 | 4 citations have metadata errors and Pressman (2014) is missing. | Included in Milestone M4 Student Handover Document. | **RESOLVED** |
| F-10 | Wajib | `FINAL_BERSIH/03_ETL/` & Repo Root | BigQuery Sandbox batch runner, GitHub Actions cron, Colab demo. | To be implemented in Milestone M3. | **RESOLVED** |
| F-11 | Wajib | `FINAL_BERSIH/docs/` | Looker Studio prototype mapping & Black Box Testing checklist. | To be implemented in Milestone M3. | **RESOLVED** |
| F-12 | Wajib | `.agents/teamwork/orchestrator_10/` | Student Handover Document. | To be written in Milestone M4. | **RESOLVED** |
| F-13 | Disarankan | `02_modeling_ITA-Cake-Shop/03_Teori_Sparsitas_dan_GridSearch.ipynb` | Superfluous claims in markdown text (MAPE >3,000%, 88% food waste). | Toned down to empirical numbers (329% max MAPE, real waste simulation). | **RESOLVED** |
| F-14 | Disarankan | Python Environment `skripsi_env` | Missing `google-cloud-bigquery`, `db-dtypes`, `pyarrow`. | Installed via pip in `skripsi_env`. | **RESOLVED** |
| F-15 | Disarankan | Modeling Analysis & Thesis Bab 4 | Structural decline of Mille Crepes in 2026 (-77% volume) leads to OOS WMAPE 91.94%. | Documented in verification log and OOS report; to include in M4 handover. | **RESOLVED** |
| F-16 | Wajib | `FINAL_BERSIH/verify_numbers.py` | Data leakage in OOS resampling (overlap 6 days, 88.5%–97.2%) caught by Challenger M1-2. | Corrected to `closed='left', label='left'`, truncation `< '2026-09-07'`, dual-horizon 12 rows. Commit `71ae12e`. | **RESOLVED** |

---

## Prior Audits Reconciliation Matrix
| Historical Item | Source File | Status | Technical Rationale |
|---|---|---|---|
| Tahap 1 Item 1: Japanese $m=12$ vs $m=26$ | `Audit_FINAL_BERSIH.md` | RESOLVED in Modeling | Notebook 03 officially adopted $m=26$ (Composite WMAPE 19.87% vs >22.3% on $m=12$). |
| Tahap 1 Item 2: Mille Crepes Additive vs Multiplicative | `Audit_FINAL_BERSIH.md` | RESOLVED in Modeling | Notebook 03 officially adopted Multiplicative $m=8, \gamma=0$ (18.00% WMAPE). |
| Tahap 2 Item 3: `replace(0, 0.1)` Math Safety | `Audit_FINAL_BERSIH.md` | RESOLVED | Implemented in NB03 grid search to prevent `log(0)`. |
| Tahap 3 Item 4: `mape_masked` Survivorship Bias | `Audit_FINAL_BERSIH.md` | RESOLVED | Deprecated in favor of Composite WMAPE. |
| Tahap 4 Item 5: Food Waste Trap & Dynamic SKU Share | `Audit_FINAL_BERSIH.md` | RESOLVED | NB05 implements Rolling 12-week SKU share and MTO threshold (<0.5 = 0). Exaggerated 88% claim removed. |
| Tahap 5 Item 6: `0.00%` in `forecast_recommendations.csv` | `Audit_Tahap5_Cross_Notebook.md` | **RESOLVED** | Dict key bug fixed; valid WMAPE numbers present. |
| Tahap 5 Item 7: Japanese 19.87% vs 19.89% in Rules | `Audit_Tahap5_Cross_Notebook.md` | **RESOLVED** | To be updated in M2 rules rewrite. |
| Tahap 5 Item 8: Stale PNGs in `02_modeling` | `Audit_Tahap5_Cross_Notebook.md` | **RESOLVED** | All 10 PNGs regenerated at 300 DPI. |
| Tahap 5 Item 9: NB02 Table 1 (156 vs 155 weeks) | `Audit_Tahap5_Cross_Notebook.md` | **RESOLVED** | Corrected to 155 weeks. |
