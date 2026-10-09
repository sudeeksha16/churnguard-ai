"""Aggregate country-level churn counts by reading partition files from HDFS."""
from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "results" / "hdfs_ready" / "bank_customers" / "manifest.json"
COMPOSE_FILE = ROOT / "hdfs" / "docker-compose.yml"
OUTPUT = ROOT / "results" / "hdfs_country_churn_summary.csv"


def read_hdfs_csv(remote_file: str) -> list[dict[str, str]]:
    command = [
        "docker", "compose", "-f", str(COMPOSE_FILE), "exec", "-T",
        "namenode", "hdfs", "dfs", "-cat", remote_file,
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8-sig")
    return list(csv.DictReader(io.StringIO(result.stdout)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hdfs-root", default="/churnguard", help="HDFS destination root used by the uploader")
    args = parser.parse_args()
    if not COMPOSE_FILE.is_file():
        raise SystemExit(f"Docker Compose file not found: {COMPOSE_FILE}")
    if not MANIFEST.is_file():
        raise SystemExit("Partition manifest not found. Run python hdfs\\prepare_data.py first.")

    root = args.hdfs_root.rstrip("/") or "/"
    partition_root = f"{root}/curated/bank_customers"
    totals: dict[str, dict[str, int]] = {}
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for partition in manifest["partitions"]:
        country = partition["country"] or "unknown"
        stats = totals.setdefault(country, {"customers": 0, "churned": 0})
        remote_file = f"{partition_root}/{partition['file']}"
        rows = read_hdfs_csv(remote_file)
        stats["customers"] += len(rows)
        stats["churned"] += sum(int(row["churn"]) for row in rows)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(["country", "customers", "churned", "stayed", "churn_rate_percent"])
        grand_total = {"customers": 0, "churned": 0}
        for country, stats in sorted(totals.items()):
            customers = stats["customers"]
            churned = stats["churned"]
            writer.writerow([country, customers, churned, customers - churned, round(100 * churned / customers, 2)])
            grand_total["customers"] += customers
            grand_total["churned"] += churned
        customers = grand_total["customers"]
        churned = grand_total["churned"]
        writer.writerow(["ALL", customers, churned, customers - churned, round(100 * churned / customers, 2)])

    print(f"Read {grand_total['customers']:,} customers from HDFS partitions.")
    print(f"Overall historical churn rate: {100 * grand_total['churned'] / grand_total['customers']:.2f}%.")
    print(f"Country summary saved to {OUTPUT}")
    print(OUTPUT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
