"""Run the country churn aggregation as a Hadoop Streaming MapReduce job."""
from __future__ import annotations

import argparse
import csv
import io
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "hdfs" / "docker-compose.yml"
MAPPER = ROOT / "hdfs" / "mapreduce_mapper.py"
REDUCER = ROOT / "hdfs" / "mapreduce_reducer.py"
STREAMING_JAR = "/opt/hadoop/share/hadoop/tools/lib/hadoop-streaming-3.5.0.jar"


def docker(*args: str, capture: bool = False) -> str:
    command = ["docker", "compose", "-f", str(COMPOSE_FILE), "exec", "-T", "namenode", *args]
    result = subprocess.run(command, check=True, text=True, encoding="utf-8", capture_output=capture)
    return result.stdout if capture else ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hdfs-root", default="/churnguard", help="HDFS root used by the uploader")
    args = parser.parse_args()
    if not COMPOSE_FILE.is_file():
        raise SystemExit(f"Docker Compose file not found: {COMPOSE_FILE}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = args.hdfs_root.rstrip("/") or "/"
    output_path = f"{root}/analytics/country_churn_mapreduce_{stamp}"
    container_mapper = "/tmp/churnguard_mapreduce_mapper.py"
    container_reducer = "/tmp/churnguard_mapreduce_reducer.py"
    container_id = subprocess.check_output(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "ps", "-q", "namenode"],
        text=True,
    ).strip()
    if not container_id:
        raise SystemExit("HDFS NameNode container is not running. Start it with docker compose up -d first.")
    subprocess.run(["docker", "cp", str(MAPPER), f"{container_id}:{container_mapper}"], check=True)
    subprocess.run(["docker", "cp", str(REDUCER), f"{container_id}:{container_reducer}"], check=True)

    docker(
        "hadoop", "jar", STREAMING_JAR,
        "-D", "mapreduce.input.fileinputformat.input.dir.recursive=true",
        "-files", f"{container_mapper},{container_reducer}",
        "-mapper", "python3 churnguard_mapreduce_mapper.py",
        "-reducer", "python3 churnguard_mapreduce_reducer.py",
        "-input", f"{root}/curated/bank_customers",
        "-output", output_path,
    )

    # Hadoop Streaming names reducer output files part-00000 (without an "r").
    output = docker("hdfs", "dfs", "-cat", f"{output_path}/part-*", capture=True)
    rows = [line.split("\t") for line in output.splitlines() if line.strip()]
    if not rows:
        raise SystemExit("MapReduce completed but produced no country summary rows.")

    local_output = ROOT / "results" / "hdfs_mapreduce_country_summary.csv"
    local_output.parent.mkdir(parents=True, exist_ok=True)
    customers_total = 0
    churned_total = 0
    with local_output.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(["country", "customers", "churned", "stayed", "churn_rate_percent"])
        for row in rows:
            if len(row) != 5:
                continue
            country, customers, churned, stayed, rate = row
            writer.writerow([country, customers, churned, stayed, rate])
            customers_total += int(customers)
            churned_total += int(churned)
        writer.writerow([
            "ALL", customers_total, churned_total, customers_total - churned_total,
            f"{100 * churned_total / customers_total:.2f}" if customers_total else "0.00",
        ])

    print(f"Hadoop MapReduce output is stored in HDFS: {output_path}")
    print(f"Processed {customers_total:,} customers; historical churn rate {100 * churned_total / customers_total:.2f}%.")
    print(f"Local report saved to {local_output}")
    print(local_output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
