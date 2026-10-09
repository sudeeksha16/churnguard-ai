"""Stream customer rows from the project CSV to a Kafka topic."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd
from kafka import KafkaProducer
from kafka.serializer import Serializer

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "Bank Customer Churn Prediction.csv"


def json_value(value: object) -> object:
    """Convert pandas/numpy scalar values into JSON-safe Python values."""
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


class StringKeySerializer(Serializer):
    def serialize(self, topic: str, headers: object, data: object) -> bytes | None:
        return None if data is None else str(data).encode("utf-8")


class CustomerJsonSerializer(Serializer):
    def serialize(self, topic: str, headers: object, data: object) -> bytes | None:
        return None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Customer CSV path")
    parser.add_argument("--topic", default="churn-customers", help="Kafka topic name")
    parser.add_argument("--broker", default="localhost:9092", help="Kafka bootstrap server")
    parser.add_argument("--delay-ms", type=int, default=25, help="Delay between records to simulate a live stream")
    parser.add_argument("--limit", type=int, default=0, help="Maximum rows to send; 0 sends all rows")
    args = parser.parse_args()

    if args.delay_ms < 0 or args.limit < 0:
        parser.error("--delay-ms and --limit must be zero or greater")
    if not args.input.is_file():
        parser.error(f"Input CSV not found: {args.input}")

    producer = KafkaProducer(
        bootstrap_servers=args.broker,
        key_serializer=StringKeySerializer(),
        value_serializer=CustomerJsonSerializer(),
        acks="all",
        retries=5,
    )
    sent = 0
    try:
        for chunk in pd.read_csv(args.input, chunksize=500):
            for record in chunk.to_dict(orient="records"):
                row = {key: json_value(value) for key, value in record.items()}
                producer.send(args.topic, key=row.get("customer_id"), value=row)
                sent += 1
                if sent % 500 == 0:
                    producer.flush()
                    print(f"Sent {sent:,} records")
                if args.limit and sent >= args.limit:
                    break
                if args.delay_ms:
                    time.sleep(args.delay_ms / 1000)
            if args.limit and sent >= args.limit:
                break
        producer.flush()
        print(f"Finished: sent {sent:,} records to topic '{args.topic}' at {args.broker}.")
    finally:
        producer.close()


if __name__ == "__main__":
    main()
