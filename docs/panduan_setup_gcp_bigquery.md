# PANDUAN LANGKAH-DEMI-LANGKAH: SETUP GOOGLE CLOUD PROJECT & BIGQUERY SANDBOX
## Panduan Konfigurasi Cloud Bebas Biaya (Tanpa Kartu Kredit) untuk Skripsi ITA Cake Shop

**Sasaran:** Google BigQuery Sandbox (100% Gratis & Legal)  
**Lingkup Kerja:** Pembuatan Proyek GCP, Inisialisasi Dataset `ita_cake_shop_dw`, & Pemahaman Batasan Sandbox  
**Bahasa:** Bahasa Indonesia  
**Penyusun:** Tim Teknis Skripsi (Worker M3)  

---

## 1. Mengenal Google BigQuery Sandbox

Google BigQuery Sandbox adalah lingkungan kerja BigQuery yang disediakan oleh Google Cloud Platform (GCP) bagi pengguna yang **tidak menautkan kartu kredit atau akun penagihan (*no billing account attached*)**.

### Karakteristik & Kuota Gratis:
1. **Penyimpanan Data Gratis:** 10 Gigabyte (GB) penyimpanan aktif gratis setiap bulan (dataset transaksi ITA Cake Shop hanya berukuran ~15 Megabyte, sehingga hanya memakai 0.15% dari kuota gratis).
2. **Pemrosesan Query Gratis:** 1 Terabyte (TB) pemrosesan query gratis setiap bulan.
3. **Batas Kedaluwarsa Tabel 60 Hari (*60-Day Table Expiration*):**
   - Setiap tabel atau partisi yang dibuat di lingkungan Sandbox otomatis memiliki masa kedaluwarsa 60 hari sejak tanggal pembuatan.
   - **Solusi Rekayasa Skripsi:** Pipeline batch mingguan (`weekly_batch.py`) menggunakan opsi `WRITE_TRUNCATE`. Setiap kali dijalankan pada hari Senin pagi (`W-MON`), tabel di-refresh secara penuh sehingga **masa kedaluwarsa 60 hari otomatis diperpanjang (di-reset) kembali**, menjamin tabel tidak akan pernah terhapus selama toko beroperasi!
4. **Pembatasan Sandbox:**
   - Tidak dapat menggunakan DML berbayar tingkat tinggi (`MERGE`, `INSERT INTO ... VALUES` streaming berbayar).
   - Tidak dapat menggunakan pemuatan langsung dari bucket Google Cloud Storage berbayar.
   - **Solusi Rekayasa Skripsi:** Pipeline menggunakan API Batch gratis `load_table_from_dataframe()` yang langsung mengunggah DataFrame dari memori runner GitHub Actions/Colab tanpa membutuhkan Cloud Storage.

---

## 2. Langkah 1: Membuat Proyek Google Cloud Baru

1. Buka browser dan login ke akun Google mahasiswa:
   👉 **https://console.cloud.google.com/**
2. Pada bilah atas (*top navigation bar*), klik dropdown pemilih proyek (di samping logo *Google Cloud Platform*).
3. Klik tombol **New Project** (Proyek Baru) di sudut kanan atas jendela pop-up.
4. Masukkan data proyek:
   - **Project Name:** `ITA Cake Shop BI`
   - **Project ID:** (Biarkan otomatis atau sesuaikan, misalnya: `ita-cake-shop-bi-2026`)
   - **Organization:** Pilih *No organization* (jika menggunakan akun Gmail pribadi).
5. Klik **Create**.
6. Tunggu notifikasi lonceng di kanan atas menunjukkan bahwa proyek berhasil dibuat, lalu klik **Select Project**.

---

## 3. Langkah 2: Mengaktifkan BigQuery API

1. Pada kotak pencarian (*search bar*) di bagian atas konsol, ketik: `BigQuery API`.
2. Klik hasil **BigQuery API**.
3. Pastikan tombol menunjukkan **Manage** (atau jika belum aktif, klik **Enable**).
4. BigQuery Sandbox kini telah aktif pada proyek Anda.

---

## 4. Langkah 3: Membuat Dataset `ita_cake_shop_dw`

1. Buka antarmuka BigQuery Studio melalui menu navigasi samping:
   👉 **Navigation Menu (☰) > BigQuery > BigQuery Studio**  
   (atau via tautan langsung: https://console.cloud.google.com/bigquery)
2. Pada panel **Explorer** di sisi kiri, klik ikon titik tiga (⋮) di samping nama Project ID Anda.
3. Pilih **Create dataset** (Buat dataset).
4. Isi formulir konfigurasi dataset berikut:
   - **Dataset ID:** `ita_cake_shop_dw` *(Wajib persis sesuai konfigurasi pipeline)*
   - **Data location:** Pilih salah satu:
     - `asia-southeast2 (Jakarta)` *(Disarankan untuk latensi terendah di Indonesia)*
     - atau `US (multiple regions in United States)` *(Default sandbox)*
   - **Enable table expiration:** Biarkan tercentang default (60 days untuk Sandbox).
5. Klik tombol biru **Create dataset**.
6. Dataset `ita_cake_shop_dw` sekarang akan muncul di panel Explorer di bawah nama project Anda.

---

## 5. Langkah 4: Verifikasi Skema & Uji Coba Query SQL

Setelah dataset terbentuk, Anda dapat menguji coba query SQL DDL pembuatan tabel dan view mart untuk Looker Studio secara manual via editor BigQuery:

```sql
-- Uji coba membuat view performa Looker Studio (dijalankan setelah tabel terunggah)
SELECT * FROM `ita_cake_shop_dw.v_looker_performance_overview` LIMIT 10;
```

---

## 6. Checklist Verifikasi Mahasiswa

- [ ] Project GCP berhasil dibuat tanpa memasukkan nomor kartu kredit.
- [ ] BigQuery API berstatus Enabled.
- [ ] Dataset `ita_cake_shop_dw` telah terbentuk di region `asia-southeast2` atau `US`.
- [ ] Project ID telah dicatat untuk digunakan pada langkah GitHub Secrets dan Looker Studio.
