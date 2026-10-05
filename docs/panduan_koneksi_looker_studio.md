# PANDUAN LANGKAH-DEMI-LANGKAH: KONEKSI BIGQUERY KE LOOKER STUDIO
## Panduan Membangun Dashboard Interaktif Prototipe ITA Cake Shop Sesuai Dokumen Sidang

**Sasaran:** Google Looker Studio (Dahulu Google Data Studio)  
**Lingkup Kerja:** Pembuatan Sumber Data BigQuery, Perakitan Halaman 1 & Halaman 2, & Penyesuaian Visual 1:1  
**Dokumen Acuan:** `Sidang/Prototype_dashboard_ITA_Cake_shop.pdf` & `FINAL_BERSIH/docs/dashboard_prototype_mapping.md`  
**Bahasa:** Bahasa Indonesia  
**Penyusun:** Tim Teknis Skripsi (Worker M3)  

---

## 1. Mengenal Google Looker Studio

Google Looker Studio adalah platform *Business Intelligence* (BI) dan visualisasi data berbasis web gratis dari Google. Looker Studio terhubung secara *native* dan bebas biaya dengan Google BigQuery, memungkinkan dashboard membaca ribuan baris data transaksi dalam hitungan milidetik secara *real-time*.

---

## 2. Langkah 1: Membuka Looker Studio & Menghubungkan Sumber Data BigQuery

1. Buka browser dan login menggunakan akun Google yang sama dengan proyek GCP Anda:
   👉 **https://lookerstudio.google.com/**
2. Klik tombol **+ Create** (Buat) di sudut kiri atas, lalu pilih **Data source** (Sumber data).
3. Pada daftar konektor Google, pilih **BigQuery**.
4. Jika diminta otorisasi, klik tombol **Authorize** (Otorisasi) untuk mengizinkan Looker Studio membaca BigQuery Anda.
5. Pada panel navigasi konektor:
   - Pilih tab: **MY PROJECTS**
   - Pilih **Project**: Nama Project ID Anda (misal: `ita-cake-shop-bi-2026`)
   - Pilih **Dataset**: `ita_cake_shop_dw`
   - Pilih **Table/View**: `v_looker_performance_overview`
6. Di sudut kanan atas, klik tombol biru **CONNECT** (Hubungkan).
7. Periksa kolom-kolom data:
   - Pastikan `order_date` bertipe **Date (YYYY-MM-DD)**.
   - Pastikan `net_amount`, `gross_amount`, `discount_amount` bertipe **Numeric / Currency (IDR - Indonesian Rupiah)**.
   - Ubah nama sumber data di kiri atas menjadi: `DS_Performance_Overview`.
8. Klik tombol **CREATE REPORT** (Buat laporan). Sebuah kanvas laporan baru akan terbuka.

---

## 3. Langkah 2: Menambahkan Sumber Data Kedua untuk Halaman 2

Sebelum mendesain visualisasi, tambahkan sumber data kedua untuk rencana produksi:
1. Di bilah menu atas Looker Studio, klik: **Resource > Manage added data sources** (Kelola sumber data yang ditambahkan).
2. Klik **+ ADD A DATA SOURCE**.
3. Pilih konektor **BigQuery > MY PROJECTS > [Project Anda] > ita_cake_shop_dw > v_looker_production_planning**.
4. Klik **CONNECT**.
5. Ubah namanya menjadi: `DS_Production_Planning`.
6. Klik **ADD TO REPORT**.

---

## 4. Langkah 3: Merakit Halaman 1 — Business Intelligence Dashboard

Beri nama Halaman 1: `Business Intelligence Dashboard`.

### A. Kontrol Filter Atas (Header & Controls):
1. **Teks Judul:** Tambahkan kotak teks (Text Box) bertuliskan `BUSINESS INTELLIGENCE DASHBOARD` (Font: Roboto/Arial, Ukuran: 20px, Tebal).
2. **Kontrol Rentang Tanggal (*Date Range Control*):**
   - Klik menu **Add a control > Date range control**.
   - Letakkan di bawah judul sebelah kiri.
   - Default date range: Auto (akan otomatis mencakup seluruh rentang penjualan).
3. **Filter Dropdown Kategori:**
   - Klik menu **Add a control > Drop-down list**.
   - Letakkan di samping kontrol tanggal.
   - **Control field:** `category_name`.
   - **Data source:** `DS_Performance_Overview`.

### B. Empat Kartu Skor KPI (Scorecards):
1. **TOTAL REVENUE:**
   - Klik **Add a chart > Scorecard**.
   - **Metric:** `net_amount` (Agregasi: SUM).
   - Pada tab **Style (Gaya)**: Centang opsi **Compact numbers** (akan menampilkan format ringkas `Rp4.05B`).
2. **TOTAL QTY SOLD:**
   - Tambahkan Scorecard kedua.
   - **Metric:** `qty_sold` (Agregasi: SUM).
   - Label: `TOTAL QTY SOLD` (Menampilkan `148,513`).
3. **TOP CATEGORY:**
   - Tambahkan Scorecard ketiga.
   - **Metric / Dimension:** `category_name`.
   - Mengambil kategori teratas berdasarkan `SUM(net_amount)` (Menampilkan `Cake`).
4. **order_no:**
   - Tambahkan Scorecard keempat.
   - **Metric:** `order_no` (Ubah agregasi menjadi `Count Distinct`).
   - Pada tab Style: Centang **Compact numbers** (Menampilkan `58.4K`).

### C. Grafik Garis Tren Omzet Harian (Line Chart):
1. Klik **Add a chart > Time series chart**.
2. **Dimension:** `order_date`.
3. **Metric:** `net_amount` (SUM).
4. Pada tab Style:
   - Warna garis: Biru (`#2b6cb0`).
   - Sumbu Y: Tetapkan nilai minimum `0`, maksimum `15,000,000`.

### D. Donut Chart (Pangsa Omzet Kategori):
1. Klik **Add a chart > Pie chart > Donut chart**.
2. **Dimension:** `category_name`.
3. **Metric:** `net_amount` (SUM).
4. Pada tab Style:
   - Slices: 10 irisan.
   - Hole size (Ukuran lubang): 40%.
   - Slice order: Berdasarkan nilai menurun.

### E. Tabel Peringkat Kinerja Produk:
1. Klik **Add a chart > Table with heatmap** (atau Table standar).
2. **Dimension:** `product_name`, `category_name`.
3. **Metric:** `qty_sold` (SUM), `net_amount` (SUM).
4. Pada tab Style:
   - Kolom `qty_sold`: Pilih tampilan **Show as Bar** (Tampilkan sebagai grafik batang data).
   - Kolom `net_amount`: Tipe mata uang IDR.
   - Pagination: 100 baris per halaman.

---

## 5. Langkah 4: Merakit Halaman 2 — Production Planning & Inventory Dashboard

Klik menu bilah kiri: **Add a page** (Tambah halaman). Beri nama: `Production Planning & Inventory Dashboard`.

### A. Tiga Kartu Skor Operasional (Scorecards):
*Pastikan sumber data seluruh komponen Halaman 2 disetel ke `DS_Production_Planning`.*

1. **TOTAL TARGET PRODUKSI (7 HARI):**
   - Tambahkan Scorecard.
   - **Metric:** `target_produksi` (Agregasi: SUM).
   - Menampilkan angka: **766** (atau sesuai pekan batch aktif).
2. **forecast_murni:**
   - Tambahkan Scorecard.
   - **Metric:** `forecast_murni` (Agregasi: SUM).
   - Menampilkan angka: **209**.
3. **safety_stock:**
   - Tambahkan Scorecard.
   - **Metric:** `safety_stock` (Agregasi: SUM).
   - Menampilkan angka: **557**.
   *(Perhatikan bahwa $209 + 557 = 766$ persis!)*

### B. Tabel Rencana Target Produksi Harian:
1. Klik **Add a chart > Table**.
2. **Dimensions:**
   - `formatted_date` (atau `forecast_date`)
   - `category_name`
   - `product_name`
3. **Metrics:**
   - `forecast_murni`
   - `safety_stock`
   - `target_produksi`
4. **Sort (Urutan):**
   - Urutkan menurun berdasarkan `target_produksi` DESC.
5. Pada tab Style:
   - Berikan pewarnaan latar belakang sel (*conditional formatting / cell color*):
     - Kolom `forecast_murni`: Nuansa biru muda.
     - Kolom `safety_stock`: Nuansa oranye muda.
     - Kolom `target_produksi`: Nuansa ungu muda.
   - Tampilkan 100 baris per halaman.

---

## 6. Langkah 5: Membagikan & Mengatur Hak Akses Dashboard

1. Di sudut kanan atas Looker Studio, klik tombol biru **Share** (Bagikan).
2. Anda dapat:
   - Membagikan tautan hanya kepada dosen pembimbing & penguji (*Restricted*).
   - Atau menyetel *Anyone with the link can view* (Siapa saja yang memiliki link dapat melihat) agar penguji dapat langsung membuka dashboard di laptop/smartphone mereka tanpa repot login.
3. Salin tautan publik dashboard tersebut untuk disertakan di Bab 4 dan Lampiran naskah skripsi Anda.

---

## 7. Checklist Verifikasi Mahasiswa

- [ ] Sumber data `DS_Performance_Overview` dan `DS_Production_Planning` terhubung tanpa pesan galat (*error*).
- [ ] Halaman 1 menampilkan angka yang cocok dengan prototipe PDF (Rp4.05B, 148,513, Cake, 58.4K).
- [ ] Halaman 2 menampilkan rencana 7 hari dan keseimbangan konsiliasi ($209 + 557 = 766$).
- [ ] Tautan publik dashboard telah dicatat dan siap dipresentasikan di sidang meja hijau.
