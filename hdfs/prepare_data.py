"""Prepare the labeled churn CSV as country/churn partitioned HDFS input."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "Bank Customer Churn Prediction.csv"
OUTPUT = ROOT / "results" / "hdfs_ready" / "bank_customers"


def partition_name(value: object) -> str:
    if pd.isna(value):
        return "unknown"
    return quote(str(value), safe="")


def main() -> None:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Project dataset not found: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    required = {"country", "churn"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing partition columns: {sorted(missing)}")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    partitions: list[dict[str, object]] = []
    grouped = df.groupby(["country", "churn"], dropna=False, sort=True)
    for (country, churn), part in grouped:
        destination = OUTPUT / f"country={partition_name(country)}" / f"churn={partition_name(churn)}" / "part-00000.csv"
        destination.parent.mkdir(parents=True, exist_ok=True)
        part.to_csv(destination, index=False)
        partitions.append({
            "country": None if pd.isna(country) else str(country),
            "churn": None if pd.isna(churn) else int(churn),
            "rows": int(len(part)),
            "file": destination.relative_to(OUTPUT).as_posix(),
        })

    manifest = {
        "source_file": DATA_PATH.name,
        "rows": int(len(df)),
        "partition_columns": ["country", "churn"],
        "columns": df.columns.tolist(),
        "partitions": partitions,
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Prepared {len(df):,} records in {len(partitions)} country/churn partitions.")
    print(f"Local HDFS-ready data: {OUTPUT}")


if __name__ == "__main__":
    main()
