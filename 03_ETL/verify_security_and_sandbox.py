#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
verify_security_and_sandbox.py
Memverifikasi:
1. Kepatuhan mutlak terhadap aturan BigQuery Sandbox (tanpa DML berbayar, tanpa GCS, WRITE_TRUNCATE aktif).
2. Konfigurasi cron GitHub Actions (Senin W-MON, cron '0 1 * * 1').
3. Secret Scan komprehensif pada seluruh file repositori (Zero Credentials Leak).
"""

import re
import sys
from pathlib import Path

def main():
    print("=" * 70)
    print("MEMULAI AUDIT KEAMANAN ZERO-CREDENTIALS & KOMPATIBILITAS SANDBOX")
    print("=" * 70)

    base_dir = Path(__file__).resolve().parent.parent

    # 1. Audit BigQuery Sandbox di weekly_batch.py
    batch_file = base_dir / "03_ETL" / "weekly_batch.py"
    assert batch_file.exists(), f"File {batch_file} tidak ditemukan!"
    script_text = batch_file.read_text(encoding="utf-8")

    assert "WRITE_TRUNCATE" in script_text, "Gagal: WRITE_TRUNCATE tidak ditemukan!"
    assert "INSERT INTO" not in script_text, "Gagal: Terdeteksi DML berbayar INSERT INTO!"
    assert "UPDATE " not in script_text, "Gagal: Terdeteksi DML berbayar UPDATE!"
    assert "DELETE FROM" not in script_text, "Gagal: Terdeteksi DML berbayar DELETE!"
    assert "gs://" not in script_text, "Gagal: Terdeteksi dependensi Cloud Storage (gs://)!"
    print("[PASS] 1. weekly_batch.py 100% patuh aturan BigQuery Sandbox (No DML, No GCS, WRITE_TRUNCATE aktif).")

    # 2. Audit GitHub Actions Workflow
    wf_file = base_dir / ".github" / "workflows" / "weekly_forecast_batch.yml"
    assert wf_file.exists(), f"File workflow {wf_file} tidak ditemukan!"
    wf_text = wf_file.read_text(encoding="utf-8")

    assert "0 1 * * 1" in wf_text, "Gagal: Penjadwalan cron bukan '0 1 * * 1' (W-MON)!"
    assert "secrets.GCP_SA_KEY" in wf_text, "Gagal: Rahasia GCP_SA_KEY tidak ditemukan di workflow!"
    assert "secrets.GCP_PROJECT_ID" in wf_text, "Gagal: Rahasia GCP_PROJECT_ID tidak ditemukan di workflow!"
    assert "secrets.GDRIVE_FOLDER_ID" in wf_text, "Gagal: Rahasia GDRIVE_FOLDER_ID tidak ditemukan di workflow!"
    print("[PASS] 2. Workflow GitHub Actions valid (W-MON cron: '0 1 * * 1', secrets terlindungi).")

    # 3. Secret Scan pada Seluruh Repositori FINAL_BERSIH
    suspicious_patterns = [
        r"-----BEGIN (?:RSA|EC|OPENSSH|PRIVATE) KEY-----",
        r'"private_key":\s*"-----BEGIN',
        r'AIza[0-9A-Za-z-_]{35}'
    ]

    leaks = []
    scanned_count = 0
    ignored_parts = {".git", "__pycache__", ".ipynb_checkpoints"}

    for p in base_dir.rglob("*"):
        if p.is_file() and not any(part in p.parts for part in ignored_parts):
            scanned_count += 1
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                for pat in suspicious_patterns:
                    if re.search(pat, content):
                        leaks.append((str(p.relative_to(base_dir)), pat))
            except Exception:
                pass

    if leaks:
        print(f"[FATAL ERROR] Ditemukan potensi kebocoran kredensial: {leaks}")
        sys.exit(1)

    print(f"[PASS] 3. Secret Scan lulus pada {scanned_count} berkas repositori: Zero Credentials Leak.")
    print("=" * 70)
    print("AUDIT KEAMANAN & SANDBOX SELESAI: SEMUA KRITERIA TERPENUHI [PASS]")
    print("=" * 70)

if __name__ == "__main__":
    main()
