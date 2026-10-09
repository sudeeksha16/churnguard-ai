"""Consume customer events from Kafka and write a local streaming snapshot."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from kafka import KafkaConsumer
from kafka.serializer import Deserializer

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "results" / "streamed_customers.jsonl"
DEFAULT_SUMMARY = ROOT / "results" / "stream_summary.json"


class CustomerJsonDeserializer(Deserializer):
    def deserialize(self, topic: str, headers: object, data: bytes | None) -> object:
        return None if data is None else json.loads(data.decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", default="churn-customers", help="Kafka topic name")
    parser.add_argument("--broker", default="localhost:9092", help="Kafka bootstrap server")
    parser.add_argument("--group", default="churnguard-analytics", help="Consumer group id")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="JSON Lines event output")
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY, help="Streaming summary JSON output")
    parser.add_argument("--max-records", type=int, default=0, help="Stop after this many events; 0 runs until interrupted")
    args = parser.parse_args()
    if args.max_records < 0:
        parser.error("--max-records must be zero or greater")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    consumer = KafkaConsumer(
        args.topic,
        bootstrap_servers=args.broker,
        group_id=args.group,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=CustomerJsonDeserializer(),
    )
    count = 0
    churn_count = 0
    by_country: Counter[str] = Counter()
    by_gender: Counter[str] = Counter()
    try:
        with args.output.open("w", encoding="utf-8") as output:
            print(f"Listening to '{args.topic}' at {args.broker}. Press Ctrl+C to stop.")
            while True:
                for message in consumer:
                    row = message.value
                    output.write(json.dumps(row, ensure_ascii=False) + "\n")
                    count += 1
                    churn_count += int(row.get("churn", 0) or 0)
                    by_country[str(row.get("country", "Unknown"))] += 1
                    by_gender[str(row.get("gender", "Unknown"))] += 1
                    if count % 100 == 0:
                        output.flush()
                        print(f"Consumed {count:,} records")
                    if args.max_records and count >= args.max_records:
                        break
                if args.max_records and count >= args.max_records:
                    break
    except KeyboardInterrupt:
        print("\nStopping consumer and saving the final summary...")
    finally:
        consumer.close()

    summary = {
        "records_consumed": count,
        "churned_records": churn_count,
        "churn_rate": churn_count / count if count else 0.0,
        "records_by_country": dict(by_country),
        "records_by_gender": dict(by_gender),
        "topic": args.topic,
        "consumer_group": args.group,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "event_file": str(args.output),
    }
    args.summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Consumed {count:,} records; wrote {args.output} and {args.summary}.")


if __name__ == "__main__":
    main()
