"""Upload prepared CSV partitions and the source CSV to a running HDFS cluster."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "Bank Customer Churn Prediction.csv"
PARTITIONS = ROOT / "results" / "hdfs_ready" / "bank_customers"
STREAM_FILE = ROOT / "results" / "streamed_customers.jsonl"
STREAM_SUMMARY = ROOT / "results" / "stream_summary.json"
COMPOSE_FILE = ROOT / "hdfs" / "docker-compose.yml"


def run_hdfs(*args: str) -> None:
    subprocess.run(["docker", "compose", "-f", str(COMPOSE_FILE), "exec", "-T", "namenode", "hdfs", "dfs", *args], check=True)


def put_file(local_file: Path, remote_file: str) -> None:
    container = subprocess.check_output(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "ps", "-q", "namenode"],
        text=True,
    ).strip()
    if not container:
        raise SystemExit("HDFS NameNode container is not running. Start it with docker compose up -d first.")
    container_path = "/tmp/churnguard-upload.csv"
    subprocess.run(["docker", "cp", str(local_file), f"{container}:{container_path}"], check=True)
    run_hdfs("-put", "-f", container_path, remote_file)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hdfs-root", default="/churnguard", help="HDFS destination root")
    args = parser.parse_args()
    if not COMPOSE_FILE.is_file():
        raise SystemExit(f"Docker Compose file not found: {COMPOSE_FILE}")
    if not PARTITIONS.is_dir():
        raise SystemExit("HDFS-ready partitions not found. Run `python hdfs/prepare_data.py` first.")
    root = args.hdfs_root.rstrip("/") or "/"
    raw_destination = f"{root}/raw"
    partition_destination = f"{root}/curated/bank_customers"

    run_hdfs("-mkdir", "-p", raw_destination)
    put_file(DATA_PATH, f"{raw_destination}/{DATA_PATH.name}")
    uploaded = 0
    for local_file in PARTITIONS.rglob("*.csv"):
        relative = local_file.relative_to(PARTITIONS).as_posix()
        remote_file = f"{partition_destination}/{relative}"
        remote_parent = remote_file.rsplit("/", 1)[0]
        run_hdfs("-mkdir", "-p", remote_parent)
        put_file(local_file, remote_file)
        uploaded += 1

    stream_destination = f"{raw_destination}/kafka"
    stream_uploads = 0
    for stream_file in (STREAM_FILE, STREAM_SUMMARY):
        if stream_file.is_file():
            run_hdfs("-mkdir", "-p", stream_destination)
            put_file(stream_file, f"{stream_destination}/{stream_file.name}")
            stream_uploads += 1
    print(f"Uploaded the raw CSV, {uploaded} partition files, and {stream_uploads} Kafka stream artifacts under {root}.")


if __name__ == "__main__":
    main()
