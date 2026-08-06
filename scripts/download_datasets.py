"""Download all 3 datasets using kagglehub (no API key needed for public datasets)."""

import os
import kagglehub
import shutil
from pathlib import Path

RAW = Path(os.environ.get("FINSIGHT_DATA_DIR", Path(__file__).resolve().parent.parent / "data" / "raw"))

DATASETS = {
    "churn": {
        "path": "blastchar/telco-customer-churn",
        "dest": RAW / "churn",
        "rename": "telco_customer_churn.csv",
    },
    "lending": {
        "path": "wordsforthewise/lending-club",
        "dest": RAW / "lending",
        "rename": "lending_club.csv",
    },
    "fraud": {
        "path": "ieee-fraud-detection",
        "type": "competition",
        "dest": RAW / "fraud",
        "rename": None,
    },
}

for name, cfg in DATASETS.items():
    print(f"\n{'='*60}")
    print(f"Downloading {name}...")
    cfg["dest"].mkdir(parents=True, exist_ok=True)

    try:
        if cfg.get("type") == "competition":
            path = kagglehub.competition_download(cfg["path"])
        else:
            path = kagglehub.dataset_download(cfg["path"])

        src = Path(path)
        print(f"  Downloaded to: {src}")

        files = list(src.rglob("*"))
        print(f"  Files found: {len(files)}")
        for f in files:
            if f.is_file():
                rel = f.relative_to(src)
                target = cfg["dest"] / rel.name
                if cfg["rename"] and rel.suffix == ".csv":
                    target = cfg["dest"] / cfg["rename"]
                shutil.copy2(f, target)
                print(f"    -> {target.name} ({target.stat().st_size / 1e6:.1f} MB)")

    except Exception as e:
        print(f"  FAILED: {e}")

print("\nDone!")
