# PANDUAN LANGKAH-DEMI-LANGKAH: SETUP SERVICE ACCOUNT & GOOGLE DRIVE
## Panduan Integrasi Kredensial Otomasi & Folder Ingesti Kasir untuk Skripsi ITA Cake Shop

**Sasaran:** Google Cloud IAM Service Account & Integrasi Google Drive API  
**Lingkup Kerja:** Akses BigQuery Otomatis, Pembuatan Kunci JSON, & Sinkronisasi File POS  
**Bahasa:** Bahasa Indonesia  
**Penyusun:** Tim Teknis Skripsi (Worker M3)  

---

## 1. Mengenal Google Service Account

*Service Account* (Akun Layanan) adalah identitas digital khusus yang digunakan oleh aplikasi (dalam hal ini runner otomatis GitHub Actions atau skrip Python) untuk berinteraksi dengan layanan Google Cloud secara aman tanpa memerlukan interaksi login manual manusia.

Akun layanan ini akan bertindak sebagai "pekerja otomatis" yang memiliki dua tugas utama:
1. Membaca file mingguan baru dari Google Drive toko.
2. Menulis dan memperbarui tabel data mart di BigQuery Sandbox.

---

## 2. Langkah 1: Mengaktifkan Google Drive API pada Proyek GCP

Agar akun layanan dapat mengakses folder Google Drive:
1. Buka konsol Google Cloud: 👉 **https://console.cloud.google.com/**
2. Pada kotak pencarian di bagian atas, ketik: `Google Drive API`.
3. Klik **Google Drive API** dari daftar hasil pencarian.
4. Klik tombol **Enable** (Aktifkan).
5. Tunggu hingga status API menjadi aktif.

---

## 3. Langkah 2: Membuat Service Account Baru

1. Masuk ke menu IAM & Admin:
   👉 **Navigation Menu (☰) > IAM & Admin > Service Accounts**  
   (atau via tautan: https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Klik tombol **+ CREATE SERVICE ACCOUNT** di bilah atas.
3. **Langkah 1 (Service account details):**
   - **Service account name:** `ita-cake-shop-batch-sa`
   - **Service account ID:** (Akan terisi otomatis, misal: `ita-cake-shop-batch-sa`)
   - **Service account description:** `Akun otomatisasi batch mingguan BigQuery dan Google Drive`
   - Klik **CREATE AND CONTINUE**.
4. **Langkah 2 (Grant this service account access to project):**
   Tambahkan dua peran (*roles*) berikut agar bot dapat mengelola BigQuery:
   - Klik dropdown *Select a role*, cari dan pilih:
     👉 **BigQuery Data Editor** (`roles/bigquery.dataEditor`)  
     *(Memberikan izin membaca dan menulis tabel ke dataset)*
   - Klik **+ ADD ANOTHER ROLE**, cari dan pilih:
     👉 **BigQuery Job User** (`roles/bigquery.jobUser`)  
     *(Memberikan izin menjalankan query dan load job)*
   - Klik **CONTINUE**.
5. **Langkah 3 (Grant users access to this service account):**
   - Biarkan kosong, klik **DONE**.

---

## 4. Langkah 3: Membuat & Mengunduh Kunci Kredensial JSON (*Key File*)

1. Pada daftar Service Accounts, cari akun yang baru saja dibuat:
   `ita-cake-shop-batch-sa@<project-id>.iam.gserviceaccount.com`
2. **Salin alamat email akun layanan tersebut ke catatan/Notepad Anda** (ini akan digunakan untuk membagikan folder Drive).
3. Klik pada nama akun layanan tersebut atau klik ikon titik tiga (⋮) di ujung kanan, pilih **Manage keys** (Kelola kunci).
4. Klik **ADD KEY > Create new key**.
5. Pilih tipe kunci: **JSON**.
6. Klik **CREATE**.
7. Browser Anda akan otomatis mengunduh berkas kunci bernama:
   `<project-id>-xxxxxxxxxxxx.json`
8. **PERINGATAN KEAMANAN KRUSIAL:**
   - Simpan berkas ini di komputer Anda dengan aman.
   - **DILARANG KERAS** memasukkan (*commit*) berkas JSON ini ke repositori Git publik maupun folder kerja skripsi yang diunggah ke internet!

---

## 5. Langkah 4: Membuat & Membagikan Folder Google Drive Kasir

Setiap hari Senin pagi, kasir atau manajer toko ITA Cake Shop akan mengunduh ekspor mingguan dari mesin Olsera POS dan meletakkannya ke Google Drive:

1. Buka Google Drive Anda: 👉 **https://drive.google.com/**
2. Klik tombol **+ Baru (+ New) > Folder baru**.
3. Beri nama folder, misalnya: `ITA_Cake_Shop_POS_Ingest`.
4. Klik **Buat**.
5. Buka folder yang baru dibuat tersebut.
6. Perhatikan bilah alamat (*address bar*) browser Anda. URL akan terlihat seperti ini:
   `https://drive.google.com/drive/folders/1a2B3c4D5e6F7g8H9i0J_kLmNoPqRsTuV`
7. **Bagian setelah `/folders/` adalah `GDRIVE_FOLDER_ID` Anda!**
   - Contoh: `1a2B3c4D5e6F7g8H9i0J_kLmNoPqRsTuV`
   - Salin string ID ini ke catatan Notepad Anda.
8. Bagikan folder ke Service Account:
   - Klik tanda panah kecil di samping nama folder di bagian atas, pilih **Bagikan (Share) > Bagikan**.
   - Pada kolom *Tambahkan orang dan grup*, **tempelkan alamat email Service Account** yang telah disalin pada Langkah 4 (misal: `ita-cake-shop-batch-sa@...iam.gserviceaccount.com`).
   - Tetapkan peran sebagai: **Editor** (atau *Viewer*).
   - Hapus centang pada *Beri tahu orang (Notify people)* jika muncul.
   - Klik **Kirim (Send / Share)**.

---

## 6. Checklist Verifikasi Mahasiswa

- [ ] Google Drive API aktif di proyek GCP.
- [ ] Service Account `ita-cake-shop-batch-sa` terbentuk dengan role *BigQuery Data Editor* & *BigQuery Job User*.
- [ ] Kunci privat JSON telah diunduh dan tersimpan aman di komputer lokal.
- [ ] Folder Google Drive `ITA_Cake_Shop_POS_Ingest` telah dibuat dan dibagikan ke email Service Account.
- [ ] `GDRIVE_FOLDER_ID` telah dicatat untuk langkah konfigurasi GitHub Secrets.
