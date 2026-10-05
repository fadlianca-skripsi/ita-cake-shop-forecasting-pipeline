# PEMETAAN 1:1 PROTOTIPE DASHBOARD LOOKER STUDIO KE BIGQUERY DATA LAYER
## Dokumentasi Arsitektur Kimball Data Mart & Pemetaan Visualisasi ITA Cake Shop Antapani

**Dokumen Rujukan:** `Sidang/Prototype_dashboard_ITA_Cake_shop.pdf`  
**Sasaran Data Layer:** Google BigQuery Sandbox (`ita_cake_shop_dw`)  
**Metodologi BI:** Ralph Kimball Dimensional Lifecycle (Star Schema + Dimensional Conformed Marts)  
**Penyusun:** Tim Teknis Skripsi (Worker M3)  
**Status:** VALIDATED & PRODUCTION-READY  

---

## 1. Ringkasan Eksekutif & Prinsip Desain

Prototipe dashboard Looker Studio ITA Cake Shop Antapani dirancang untuk menyajikan dua perspektif manajemen yang berbeda:
1. **Halaman 1 (Tingkat Makro / Strategis):** *Business Intelligence Dashboard* yang menyajikan evaluasi kinerja penjualan historis toko (Februari 2023 s.d. Februari 2026 / September 2026), pola musiman omzet harian, distribusi kategori produk, dan peringkat kontribusi produk.
2. **Halaman 2 (Tingkat Mikro / Operasional):** *Production Planning & Inventory Dashboard* yang menyajikan proyeksi kebutuhan produksi harian per SKU selama 7 hari kalender ke depan (Senin s.d. Minggu) berbasis model *Holt-Winters Multiplicative*, persediaan pengaman (*safety stock* $Z=1.65$), dan pemutus limbah *Made-to-Order* (MTO Threshold).

Seluruh elemen visual dipetakan secara ketat dan konsisten ke dalam arsitektur **Star Schema Kimball** pada dataset `ita_cake_shop_dw` melalui dua *Analytical Mart Views*:
- `v_looker_performance_overview` (Mendukung 100% visual Halaman 1)
- `v_looker_production_planning` (Mendukung 100% visual Halaman 2)

---

## 2. Arsitektur Star Schema Kimball Data Mart

```
                    ┌────────────────────────────┐
                    │          dim_date          │
                    ├────────────────────────────┤
                    │ PK: date_id (INT64)        │
                    │     tanggal_penuh (DATE)   │
                    │     nama_hari (STRING)     │
                    │     nama_bulan (STRING)    │
                    │     minggu_ke (INT64)      │
                    │     tahun (INT64)          │
                    │     is_weekend (BOOL)      │
                    │     is_idulfitri (BOOL)    │
                    └─────────────┬──────────────┘
                                  │ 1
                                  │
                                  │ *
┌────────────────────────────┐    ┌───────────────────────────────┐
│        dim_product         │    │          fact_sales           │
├────────────────────────────┤    ├───────────────────────────────┤
│ PK: product_id (INT64)     │1  *│ FK: order_no (STRING)         │
│     product_name (STRING)  ├────┤ FK: date_id (INT64)           │
│     category_name (STRING) │    │ FK: product_id (INT64)        │
│     sell_price_curr (NUM)  │    │     unit_price (NUMERIC)      │
│     scd_type (STRING)      │    │     qty_sold (INT64)          │
│     is_active_12w (BOOL)   │    │     gross_amount (NUMERIC)    │
└────────────────────────────┘    │     discount_amount (NUMERIC) │
                                  │     net_amount (NUMERIC)      │
                                  └───────────────────────────────┘
                                                  
                                                  
┌─────────────────────────────────────────────────────────────────┐
│                      plan_production_daily                      │
├─────────────────────────────────────────────────────────────────┤
│ PK: (forecast_date, product_name)                               │
│     forecast_date (DATE)                                        │
│     category_name (STRING)                                      │
│     product_name (STRING)                                       │
│     forecast_murni (INT64)                                      │
│     safety_stock (INT64)                                        │
│     target_produksi (INT64)                                     │
│     batch_execution_timestamp (TIMESTAMP)                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Pemetaan Detail Elemen Halaman 1: Business Intelligence Dashboard

Halaman 1 berfokus pada analisis historis omzet toko. Seluruh komponen bersumber dari view analitis `v_looker_performance_overview`.

```sql
CREATE OR REPLACE VIEW `ita_cake_shop_dw.v_looker_performance_overview` AS
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
FROM `ita_cake_shop_dw.fact_sales` f
JOIN `ita_cake_shop_dw.dim_date` d ON f.date_id = d.date_id
JOIN `ita_cake_shop_dw.dim_product` p ON f.product_id = p.product_id;
```

### Matriks Pemetaan Elemen Halaman 1 (Visual ke SQL)

| No | Elemen Visual di PDF | Tipe Komponen di Looker Studio | Nilai Display di Prototipe | Sumber Field / Rumus Agregasi SQL | Konfigurasi Formatting Looker Studio |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | **Filter Tanggal** | Date Range Control | `Select date range` (Default: Auto) | `order_date` | Date format: YYYY-MM-DD |
| **2** | **Filter Kategori** | Dropdown List Control | `category_name` | `category_name` | Search enabled, multiple selection |
| **3** | **Scorecard TOTAL REVENUE** | Scorecard | **Rp4.05B** | `SUM(net_amount)` | Tipe data: Currency (IDR), Compact Numbers = ON |
| **4** | **Scorecard TOTAL QTY SOLD** | Scorecard | **148,513** | `SUM(qty_sold)` | Tipe data: Number, Format = Decimal Integer |
| **5** | **Scorecard TOP CATEGORY** | Scorecard | **Cake** | Dimensi: `category_name`<br>Metrik: `SUM(net_amount)` | Urutkan berdasarkan `SUM(net_amount)` DESC, ambil baris teratas |
| **6** | **Scorecard order_no** | Scorecard | **58.4K** | `COUNT_DISTINCT(order_no)` | Tipe data: Number, Compact Numbers = ON |
| **7** | **Tren Omzet Harian** | Time Series Line Chart | Fluktuasi kurva harian (0 s.d. 15M) | Dimensi: `order_date`<br>Metrik: `SUM(net_amount)` | Rentang sumbu Y: 0 - 15,000,000 IDR, Garis kurva biru (#2b6cb0) |
| **8** | **Pangsa Omzet Kategori** | Donut Chart | Irisan 10 kategori:<br>- Cake: 26.1%<br>- Japanese: 16.0%<br>- Custom: 13.8%<br>- Mille Crepes: 7.8%<br>- Mochi: 5.7%<br>- Coklat: 5.1%<br>- Cookies: 4.0%<br>- Puding: 3.3%<br>- Macaron: 3.3%<br>- Others: 14.8% | Dimensi: `category_name`<br>Metrik: `SUM(net_amount)` | Tampilkan persentase slice, lubang donat 40%, urutan kontribusi menurun |
| **9** | **Tabel Kinerja Produk** | Table with Data Bars | Top 5 teratas:<br>1. Mille Crepes Slice (11,013 pcs / Rp197.8M)<br>2. Soft Cookies (10,107 pcs / Rp100.7M)<br>3. Mochi Daifuku Pouch (8,868 pcs / Rp63.5M)<br>4. Cup Cake Mika Bulat (8,858 pcs / Rp55.8M)<br>5. Lilin Spiral (8,623 pcs / Rp21.5M)<br>Pagination: 1-100 / 2,161 | Dimensi:<br>- `product_name`<br>- `category_name`<br>Metrik:<br>- `SUM(qty_sold)` (Data Bar)<br>- `SUM(net_amount)` (Currency) | Urutan sorting: `SUM(qty_sold)` DESC. Batas baris per halaman: 100 baris. |

---

## 4. Pemetaan Detail Elemen Halaman 2: Production Planning & Inventory Dashboard

Halaman 2 berfokus pada rencana operasional pabrikasi/dapur untuk 7 hari ke depan. Seluruh komponen bersumber dari view operasional `v_looker_production_planning`.

```sql
CREATE OR REPLACE VIEW `ita_cake_shop_dw.v_looker_production_planning` AS
SELECT
    PARSE_DATE('%Y-%m-%d', forecast_date) AS forecast_date,
    category_name,
    product_name,
    forecast_murni,
    safety_stock,
    target_produksi,
    FORMAT_DATE('%a, %d %b %Y', PARSE_DATE('%Y-%m-%d', forecast_date)) AS formatted_date,
    batch_execution_timestamp
FROM `ita_cake_shop_dw.plan_production_daily`
ORDER BY forecast_date ASC, target_produksi DESC;
```

### Matriks Pemetaan Elemen Halaman 2 (Visual ke SQL)

| No | Elemen Visual di PDF | Tipe Komponen di Looker Studio | Nilai Display di Prototipe | Sumber Field / Rumus Agregasi SQL | Konfigurasi Formatting Looker Studio |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | **Scorecard TOTAL TARGET** | Scorecard | **766** | `SUM(target_produksi)` | Target fisik keseluruhan 7 hari kalender (Format: Number) |
| **2** | **Scorecard forecast_murni** | Scorecard | **209** | `SUM(forecast_murni)` | Ramalan baseline murni tanpa buffer (Format: Number) |
| **3** | **Scorecard safety_stock** | Scorecard | **557** | `SUM(safety_stock)` | Penyangga varians residual Service Level 95% (Format: Number) |
| **-** | *Uji Konsiliasi Matematis* | *Verifikasi Integritas* | **$209 + 557 = 766$** | `forecast_murni + safety_stock = target_produksi` | Konsiliasi penjumlahan terverifikasi tepat 100% |
| **4** | **Tabel Rencana Produksi Harian** | Table with Heatmap / Bars | Kolom tertera:<br>- `forecast_date`<br>- `category_name`<br>- `product_name`<br>- `forecast_murni`<br>- `safety_stock`<br>- `target_produksi`<br>Contoh baris teratas:<br>Feb 13, MC Slice (9, 19, 28)<br>Feb 14, MC Slice (8, 19, 27)<br>Feb 15, MC Slice (7, 19, 26)<br>Feb 10, MC Slice (7, 19, 26)<br>Feb 11, MC Slice (6, 19, 25)<br>Feb 16, MC Slice (5, 19, 24)<br>Feb 12, MC Slice (5, 19, 24)<br>Feb 15, Japanese (5, 7, 12)<br>Pagination: 1-100 / 291 | Dimensi:<br>- `formatted_date`<br>- `category_name`<br>- `product_name`<br>Metrik:<br>- `forecast_murni`<br>- `safety_stock`<br>- `target_produksi` | Urutan sorting: `target_produksi` DESC. Pewarnaan sel (conditional formatting / heatmap): ungu untuk target_produksi, oranye untuk safety_stock, biru untuk forecast_murni. Batas: 100 baris. |

---

## 5. Ringkasan Sinkronisasi Kolom & Tipe Data

| BigQuery Table / View | Nama Kolom | Tipe Data SQL | Tipe Data di Looker Studio | Keterangan Bisnis |
| :--- | :--- | :--- | :--- | :--- |
| `dim_date` | `date_id` | `INT64` | Number | Surrogate key tanggal format YYYYMMDD |
| `dim_date` | `tanggal_penuh` | `STRING` / `DATE` | Date | Tanggal kalender harian |
| `dim_date` | `nama_hari` | `STRING` | Text | Nama hari dalam Bahasa Inggris (Monday..Sunday) |
| `dim_date` | `nama_bulan` | `STRING` | Text | Nama bulan (February..September) |
| `dim_date` | `is_weekend` | `BOOL` | Boolean | True jika Sabtu atau Minggu |
| `dim_product` | `product_id` | `INT64` | Number | Surrogate key produk |
| `dim_product` | `product_name` | `STRING` | Text | Nama SKU produk terdaftar |
| `dim_product` | `category_name`| `STRING` | Text | Kategori produk Olsera |
| `dim_product` | `is_active_12w`| `BOOL` | Boolean | True jika terjual >0 unit dalam 84 hari terakhir |
| `fact_sales` | `order_no` | `STRING` | Text | Nomor faktur / struk transaksi POS |
| `fact_sales` | `qty_sold` | `INT64` | Number | Jumlah fisik kue terjual |
| `fact_sales` | `net_amount` | `NUMERIC` | Currency (IDR) | Omzet riil setelah potongan diskon |
| `plan_production_daily`| `forecast_date` | `DATE` | Date | Tanggal eksekusi rencana produksi |
| `plan_production_daily`| `forecast_murni`| `INT64` | Number | Nilai peramalan dasar |
| `plan_production_daily`| `safety_stock` | `INT64` | Number | Cadangan pengaman Service Level 95% |
| `plan_production_daily`| `target_produksi`| `INT64` | Number | Target batch pembuatan kue di dapur |

---
*Dokumentasi ini disahkan sebagai spesifikasi teknis resmi penghubung Data Layer BigQuery dengan Looker Studio.*
