"""Uncompress lending club CSV and clean up."""

import os
from pathlib import Path
import gzip
import shutil

RAW = Path(os.environ.get("FINSIGHT_DATA_DIR", Path(__file__).resolve().parent.parent / "data" / "raw"))

# 1) Uncompress Lending Club
lending_gz = RAW / "lending" / "accepted_2007_to_2018Q4.csv.gz"
lending_csv = RAW / "lending" / "lending_club.csv"

if lending_gz.exists() and not lending_csv.exists():
    with gzip.open(lending_gz, "rt") as fin, open(lending_csv, "w", newline="") as fout:
        shutil.copyfileobj(fin, fout)
    mb = lending_csv.stat().st_size / 1e6
    print(f"Uncompressed: {lending_csv.name} ({mb:.0f} MB)")

# 2) Remove rejected file (not needed)
rejected = RAW / "lending" / "rejected_2007_to_2018Q4.csv.gz"
if rejected.exists():
    rejected.unlink()
    print("Removed rejected_2007_to_2018Q4.csv.gz")

# 3) Check churn header
churn_csv = RAW / "churn" / "telco_customer_churn.csv"
if churn_csv.exists():
    with open(churn_csv) as f:
        header = f.readline().strip()
    cols = header.split(",")
    print(f"Churn: {len(cols)} columns -> {cols}")

# 4) Check lending columns (first 5MB)
if lending_csv.exists():
    with open(lending_csv) as f:
        header = f.readline().strip()
    cols = header.split(",")
    print(f"Lending: {len(cols)} columns")
    print(f"  First 10: {cols[:10]}")
    print(f"  Has loan_status: {'loan_status' in cols}")
    print(f"  Has credit_score: {'credit_score' in cols or 'fico_range_low' in cols or 'fico_range_high' in cols}")

print("\nDone!")
