# Kafka streaming stage

The producer streams the project CSV as JSON customer events. The consumer saves the received events as JSON Lines and writes a compact summary. Both scripts use the local Kafka broker at `localhost:9092` by default.

## Run

Start a Kafka broker first, then open two PowerShell windows from the project directory.

Window 1 — start the consumer before producing records:

```powershell
python kafka\consumer.py --max-records 10000
```

Window 2 — stream the dataset, paced at 25 ms per event by default:

```powershell
python kafka\producer.py
```

For a quick connection check, send a small sample:

```powershell
python kafka\consumer.py --max-records 20
python kafka\producer.py --limit 20 --delay-ms 0
```

The consumer writes `results/streamed_customers.jsonl` and `results/stream_summary.json`. Stop a continuous consumer with Ctrl+C; it saves a summary on shutdown. To use a broker elsewhere, pass the same `--broker host:port` to both scripts.

The CSV contains historical outcomes, so stream summaries describe this labeled dataset. This demo does not simulate real-time customer activity or establish a future churn horizon.
