# PANDUAN LANGKAH-DEMI-LANGKAH: SETUP REPOSITORI GITHUB PRIVAT & ACTIONS SECRETS
## Panduan Otomatisasi Batch Mingguan Terjadwal (W-MON Cron) Tanpa Kebocoran Kredensial

**Sasaran:** GitHub Actions Workflows & GitHub Repository Secrets  
**Lingkup Kerja:** Penjadwalan Tiap Senin (`cron: '0 1 * * 1'`), Enkripsi Kunci Base64, & Demonstrasi Sidang  
**Bahasa:** Bahasa Indonesia  
**Penyusun:** Tim Teknis Skripsi (Worker M3)  

---

## 1. Mengenal GitHub Actions & Konsep Zero-Credentials

Pipeline peramalan permintaan ITA Cake Shop dirancang untuk beroperasi secara mandiri setiap Senin pagi tanpa perlu ada staf yang membuka laptop atau menjalankan skrip Python secara manual.

Untuk menjaga integritas akademik dan keamanan informasi bisnis UMKM:
1. Repositori kode **wajib disetel ke mode PRIVAT (*Private Repository*)**.
2. **Protokol Zero-Credentials:** Tidak ada file kunci `.json`, kata sandi, atau token yang boleh di-commit ke repositori Git. Seluruh variabel sensitif disimpan pada brankas terenkripsi bawaan GitHub bernama **Repository Secrets**.

---

## 2. Langkah 1: Menyiapkan Repositori GitHub Privat

1. Login ke akun GitHub Anda: 👉 **https://github.com/**
2. Buat repositori baru (*New Repository*):
   - **Repository name:** `ita-cake-shop-forecasting-pipeline` (atau sesuaikan)
   - **Visibility:** Pilih **Private** 🔒 *(Sangat Krusial)*
   - Klik **Create repository**.
3. Hubungkan folder `FINAL_BERSIH` lokal ke repositori GitHub Anda:
   ```powershell
   cd "c:\Users\admin\Documents\Semester 8 & 9\Skripsi(2)\FINAL_BERSIH"
   git remote add origin https://github.com/<username-github>/ita-cake-shop-forecasting-pipeline.git
   git branch -M main
   git push -u origin main
   ```

---

## 3. Langkah 2: Mengonversi Kunci Service Account JSON ke Format Base64

GitHub Actions Secrets bekerja paling andal saat file JSON dikonversi menjadi satu baris teks string terenkripsi Base64.

### Di Komputer Windows (Menggunakan PowerShell):
1. Buka PowerShell di laptop Anda.
2. Jalankan perintah satu baris berikut (sesuaikan path file JSON kunci yang telah diunduh):
   ```powershell
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\Users\admin\Downloads\<nama-kunci-gcp>.json")) | Set-Clipboard
   ```
3. *Perintah di atas otomatis menyalin teks Base64 ke Clipboard Anda!* (Anda siap menempelkannya/paste langsung ke GitHub).

### Di Komputer Linux / Mac / Google Cloud Shell:
```bash
base64 -w 0 <nama-kunci-gcp>.json
```

---

## 4. Langkah 3: Menambahkan Tiga Kunci Rahasia di GitHub Secrets

1. Buka halaman repositori GitHub Anda di browser.
2. Klik tab **Settings** (Pengaturan di bilah kanan atas repositori).
3. Pada menu samping kiri, klik **Secrets and variables > Actions**.
4. Klik tombol hijau **New repository secret**.
5. Masukkan rahasia pertama:
   - **Name:** `GCP_PROJECT_ID`
   - **Secret:** Tempelkan ID proyek Google Cloud Anda (misal: `ita-cake-shop-bi-2026`).
   - Klik **Add secret**.
6. Klik tombol **New repository secret** lagi untuk rahasia kedua:
   - **Name:** `GCP_SA_KEY`
   - **Secret:** Tempelkan (*paste*) teks string Base64 yang sudah disalin pada Langkah 2.
   - Klik **Add secret**.
7. Klik tombol **New repository secret** lagi untuk rahasia ketiga:
   - **Name:** `GDRIVE_FOLDER_ID`
   - **Secret:** Tempelkan string ID folder Google Drive kasir (yang disalin dari URL Google Drive).
   - Klik **Add secret**.

Sekarang brankas GitHub Actions Anda telah memiliki 3 rahasia resmi:
- `GCP_PROJECT_ID`
- `GCP_SA_KEY`
- `GDRIVE_FOLDER_ID`

---

## 5. Langkah 4: Memahami Jadwal Otomasi Cron Mingguan

Workflow otomatis telah didefinisikan pada file:  
`.github/workflows/weekly_forecast_batch.yml`

```yaml
on:
  schedule:
    # Berjalan otomatis setiap hari Senin pukul 01:00 UTC (08:00 WIB)
    - cron: '0 1 * * 1'
  workflow_dispatch: # Tombol pemicu manual untuk demonstrasi sidang
```

- **01:00 UTC = 08:00 WIB (Waktu Indonesia Barat):**  
  Tepat 1 jam sebelum dapur ITA Cake Shop mulai beroperasi (pukul 09:00 WIB), server GitHub di cloud secara otomatis menyala, mengunduh transaksi mingguan baru, menjalankan Holt-Winters dan disagregasi anti-limbah, lalu memperbarui tabel BigQuery Sandbox.
- Manajer dan kepala dapur cukup membuka dashboard Looker Studio di HP/tablet mereka pada pukul 08:15 WIB dan rencana produksi 7 hari sudah langsung tersaji!

---

## 6. Langkah 5: Cara Menjalankan Eksekusi Manual (*Workflow Dispatch*) saat Sidang Skripsi

Saat dosen penguji meminta Anda mendemonstrasikan sistem secara langsung di ruang sidang:
1. Buka repositori GitHub Anda di browser.
2. Klik tab **Actions** di bilah atas.
3. Di panel sebelah kiri, klik workflow: **Weekly Demand Forecasting & BigQuery Batch Pipeline**.
4. Anda akan melihat bilah biru dengan tombol dropdown: **Run workflow ▼**.
5. Klik **Run workflow**. Anda dapat memilih:
   - Centang opsi *Dry-Run* jika ingin demonstrasi simulasi cepat tanpa mengirim data ke GCP.
   - Atau biarkan default untuk langsung menyinkronkan data ke BigQuery nyata.
6. Klik tombol hijau **Run workflow**.
7. Dalam beberapa detik, antrean job akan muncul dan ikon kuning akan berputar.
8. Klik pada nama job tersebut untuk melihat log proses *real-time* yang sedang membaca data, menghitung Holt-Winters, dan menulis data ke BigQuery.
9. Ketika selesai (ikon berubah menjadi centang hijau ✅), buka Looker Studio dan tunjukkan angka yang baru saja ter-refresh kepada dewan penguji!

---

## 7. Checklist Verifikasi Mahasiswa

- [ ] Repositori GitHub telah dibuat dan berstatus Private.
- [ ] Tiga rahasia (`GCP_PROJECT_ID`, `GCP_SA_KEY`, `GDRIVE_FOLDER_ID`) terpasang rapi di GitHub Secrets.
- [ ] File `.github/workflows/weekly_forecast_batch.yml` telah di-push ke branch utama (`main`).
- [ ] Tombol manual *Run workflow* telah dicoba satu kali dan menghasilkan status centang hijau (Success).
