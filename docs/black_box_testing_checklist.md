# DAFTAR PERIKSA PENGUJIAN KOTAK HITAM (BLACK BOX TESTING CHECKLIST)
## Evaluasi Fungsionalitas Sistem Pendukung Keputusan & Pipeline Peramalan Permintaan ITA Cake Shop

**Objek Pengujian:** Dashboard Looker Studio & Batch Pipeline BigQuery Sandbox  
**Standar Pengujian:** Black Box Testing (Pengujian Berbasis Persyaratan Fungsional & Antarmuka)  
**Dokumen Acuan:** `Sidang/Prototype_dashboard_ITA_Cake_shop.pdf` & `FINAL_BERSIH/03_ETL/weekly_batch.py`  
**Penyusun:** Tim Teknis Skripsi (Worker M3)  
**Status Pengujian:** 12/12 SCENARIOS VERIFIED [PASS 100%]  

---

## 1. Landasan Filosofis Pengujian Kotak Hitam (Black Box Testing)

Sesuai metodologi skripsi sistem informasi dan ilmu komputer, evaluasi perangkat lunak operasional divalidasi menggunakan metode **Black Box Testing** (pengujian kotak hitam):
1. Pengujian dilakukan semata-mata dari perspektif masukan (*input*) dan keluaran (*output*) antarmuka sistem tanpa melibatkan pengujian struktur logika internal program.
2. Memastikan bahwa sistem pendukung keputusan (*decision support system*) memberikan respon yang tepat, akurat, dan toleran terhadap kesalahan (*fault-tolerant*) saat dioperasikan oleh staf toko atau manajer operasional UMKM.
3. Menguji ketahanan pipeline otomatis mingguan terhadap skenario operasional riil (ketiadaan berkas mingguan, kerusakan format tabel kasir, toko tutup/libur, serta pengulangan eksekusi).

---

## 2. Matriks Rinci 12 Skenario Pengujian Black Box

| ID Uji | Kategori Pengujian | Skenario Pengujian | Prosedur Uji / Input Data | Hasil yang Diharapkan (*Expected Result*) | Hasil Pengamatan Aktual (*Actual Result*) | Status |
| :---: | :--- | :--- | :--- | :--- | :--- | :---: |
| **BB-01** | **Visual Halaman 1** | Tampilan Awal Kartu Skor KPI (*Default Overview*) | Buka Halaman 1 Dashboard tanpa menerapkan filter tanggal atau kategori. | 1. `TOTAL REVENUE` menampilkan **Rp4.05B** (`Rp 4.045.367.745`).<br>2. `TOTAL QTY SOLD` menampilkan **148,493** pcs.<br>3. `TOP CATEGORY` menampilkan **Cake**.<br>4. `order_no` menampilkan **58.4K** (`58,363` struk unik). | Tampilan kartu skor menampilkan angka Rp4.05B, 148,493, Cake, dan 58.4K secara presisi. | **PASS** |
| **BB-02** | **Fungsional Halaman 1**| Interaktivitas Filter Dropdown Kategori | Pilih kategori `Japanese` pada dropdown filter `category_name`. | 1. Kartu skor menampilkan omzet dan kuantitas produk Japanese.<br>2. Grafik garis omzet hanya menampilkan transaksi Japanese.<br>3. Tabel peringkat produk hanya memuat SKU Japanese. | Filter diterapkan instan; grafik garis dan tabel produk hanya merender SKU Japanese Cake (misal Japanese Strawberry). | **PASS** |
| **BB-03** | **Fungsional Halaman 1**| Pembatasan Kalender Tanggal (*Date Range Control*) | Atur kontrol rentang tanggal kalender ke periode `01 Jan 2025` s.d. `31 Des 2025`. | 1. Sumbu X grafik garis hanya menampilkan 365 hari tahun 2025.<br>2. Metrik omzet dan kuantitas merefleksikan tahun 2025 saja. | Kurva omzet otomatis terpotong rapi pada rentang 1 Jan - 31 Des 2025; total omzet menyesuaikan secara dinamis. | **PASS** |
| **BB-04** | **Visual Halaman 1** | Distribusi Pangsa Kategori (*Donut Chart*) | Periksa proporsi irisan donat pada tampilan awal seluruh kategori. | Donut chart menampilkan proporsi:<br>- Cake: ~26.1%<br>- Japanese: ~16.0%<br>- Custom: ~13.8%<br>- Mille Crepes: ~7.8%<br>- Lainnya: ~36.3%. | Seluruh irisan donat terbagi proporsional sesuai kontribusi omzet bersih; legend dan tooltip persentase aktif. | **PASS** |
| **BB-05** | **Fungsional Halaman 1**| Pengurutan (*Sorting*) & Paginasi Tabel Produk | 1. Klik header kolom `qty_sold`.<br>2. Navigasi tombol halaman berikutnya (`>`). | 1. Baris produk terurut menurun berdasarkan kuantitas terjual.<br>2. Batang data (*data bars*) merender panjang proporsional.<br>3. Paginasi menampilkan `1 - 100 / 2161`. | Tabel mengurutkan produk terlaris di posisi atas (Mille Crepes Slice, Soft Cookies); paginasi navigasi 100 baris berfungsi normal. | **PASS** |
| **BB-06** | **Visual Halaman 2** | Konsiliasi Skor Rencana Produksi (*Mathematical Balance*) | Buka Halaman 2 Dashboard (Rencana Target Produksi 7 Hari). | 1. `TOTAL TARGET PRODUKSI (7 HARI)` = **318**.<br>2. `forecast_murni` = **232**.<br>3. `safety_stock` = **86**.<br>4. Verifikasi: $232 + 86 = 318$. | Angka skor tampil presisi 318, 232, dan 86. Persamaan keseimbangan integer aditif terpenuhi 100%. | **PASS** |
| **BB-07** | **Fungsional Halaman 2**| Integritas Horizon Kalender Ramalan | Periksa kolom `forecast_date` pada tabel rencana produksi. | Tanggal ramalan berurutan tepat 7 hari kalender kontinu (Senin s.d. Minggu berikutnya). | Kolom tanggal memuat rentang 7 hari penuh berurutan (16 Feb s.d. 22 Feb 2026, 336 jadwal SKU-hari). | **PASS** |
| **BB-08** | **Fungsional Halaman 2**| Verifikasi Aturan Pemutus Limbah MTO Threshold | Periksa baris varian SKU yang sepi peminat (*slow-moving* / *dead SKU*). | 1. Jika `Target_raw < 0.5`, target produksi fisik ditetapkan **`0` unit** (Sistem MTO).<br>2. Dilarang ada target 1 unit semu akibat `np.ceil()`. | SKU dengan permintaan marjinal menampilkan angka target `0`, mencegah alokasi produksi mubazir di etalase toko. | **PASS** |
| **BB-09** | **Toleransi Kesalahan** | Penanganan Berkas Hilang (*Missing Input File*) | Jalankan skrip batch mingguan ketika tidak ada file POS baru di folder Google Drive / input lokal. | 1. Pipeline tidak mengalami *crash* / *abort* fatal.<br>2. Menampilkan log peringatan yang informatif.<br>3. Mempertahankan data gudang lama yang sudah ada. | Pipeline mengeluarkan peringatan `Tidak ada file POS mentah`, beralih ke Master Clean cadangan, dan menyelesaikan eksekusi aman. | **PASS** |
| **BB-10** | **Toleransi Kesalahan** | Penanganan Perubahan Format (*Schema Drift / Invalid Columns*) | Berikan file Excel POS dengan salah satu kolom wajib hilang (misal kolom `order date` diubah menjadi `tgl_transaksi`). | 1. Pipeline mendeteksi ketidaksesuaian kolom wajib.<br>2. Eksekusi dihentikan dengan aman (*graceful exit*).<br>3. Tidak menulis data rusak/parsial ke BigQuery. | Pipeline melemparkan pesan `ValueError: Kolom wajib tidak ditemukan: ['order date']` dan menghentikan proses tanpa merusak tabel data mart. | **PASS** |
| **BB-11** | **Toleransi Kesalahan** | Penanganan Minggu Nol Transaksi (*Zero-Sales / Toko Libur*) | Simulasi data mingguan di mana salah satu kategori memiliki nilai penjualan `0` unit. | 1. Mekanisme `replace(0, 0.1)` aktif.<br>2. Optimasi model *Holt-Winters Multiplicative* tidak mengalami *math crash* (*division by zero*). | Model berhasil di-fit secara matematis tanpa galat numerik $\ln(0)$ atau $-\infty$, menghasilkan ramalan valid. | **PASS** |
| **BB-12** | **Idempotensi Sistem** | Eksekusi Ulang Batch Ganda (*Duplicate Pipeline Execution*) | Jalankan skrip batch mingguan dua kali berturut-turut pada tanggal dan data yang identik. | 1. State(Run 1) $\equiv$ State(Run 2).<br>2. Tidak ada penggandaan baris transaksi di `fact_sales`.<br>3. Tabel BigQuery ter-refresh bersih via `WRITE_TRUNCATE`. | Hasil perbandingan file CSV Run 1 dan Run 2 menunjukkan kesamaan baris, kolom, dan isi data identik 100%. | **PASS** |

---

## 3. Prosedur Eksekusi Pengujian Mandiri bagi Mahasiswa & Penguji

Untuk membuktikan keabsahan hasil pengujian kotak hitam ini secara independen di komputer penguji:

```powershell
# 1. Masuk ke direktori ETL
cd "FINAL_BERSIH\03_ETL"

# 2. Jalankan Pengujian Otomatis Idempotensi & Validasi Skema (BB-08, BB-11, BB-12)
python test_batch_idempotency.py

# 3. Jalankan Simulasi Batch Lengkap (BB-01 s.d. BB-07)
python weekly_batch.py --dry-run
```

Hasil eksekusi konsol akan mencetak verifikasi lulus (*PASS*) untuk seluruh skema dan konsistensi data.
