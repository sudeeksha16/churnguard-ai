"""Hadoop Streaming reducer: aggregate customers and churn by country."""
from __future__ import annotations

import sys


current_country: str | None = None
customers = 0
churned = 0


def emit(country: str, customer_count: int, churn_count: int) -> None:
    stayed = customer_count - churn_count
    rate = 100 * churn_count / customer_count if customer_count else 0.0
    print(f"{country}\t{customer_count}\t{churn_count}\t{stayed}\t{rate:.2f}")


for line in sys.stdin:
    fields = line.rstrip("\n").split("\t")
    if len(fields) != 3:
        continue
    country, customer_value, churn_value = fields
    if current_country is not None and country != current_country:
        emit(current_country, customers, churned)
        customers = 0
        churned = 0
    current_country = country
    customers += int(customer_value)
    churned += int(churn_value)

if current_country is not None:
    emit(current_country, customers, churned)
