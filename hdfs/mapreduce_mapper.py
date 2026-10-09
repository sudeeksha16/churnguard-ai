"""Hadoop Streaming mapper: emit (country, customer count, churn count)."""
from __future__ import annotations

import csv
import sys


for line in sys.stdin:
    try:
        row = next(csv.reader([line]))
        if not row:
            continue
        if row[0].strip().lower() == "customer_id":
            continue
        # The prepared CSV schema has country and churn columns in every file.
        # Their positions are read from the known project dataset schema.
        country = row[2].strip()
        churn = int(row[-1].strip())
        print(f"{country}\t1\t{churn}")
    except (ValueError, IndexError, csv.Error) as exc:
        print(f"Skipping malformed input row: {exc}", file=sys.stderr)
