# Kafka Streaming Pipeline (PS 45 Ingestion)

This stage implements the official PS 45 objective: **Ingest customer account and transaction activity through Apache Kafka**.

The producer reads customer rows from `data/Bank Customer Churn Prediction.csv` and serializes them as JSON events onto topic `churn-customers`. The consumer subscribes to the topic, persists the records to `results/streamed_customers.jsonl`, and computes an event summary in `results/stream_summary.json`.

---

## 1. Start the Kafka Broker (Docker Compose, KRaft Mode)

A dedicated, lightweight Apache Kafka broker configured in **KRaft mode** (no ZooKeeper required) is provided in `kafka/docker-compose.yml`.

Ensure Docker Desktop is running, then execute from the project root:

```powershell
docker compose -f kafka/docker-compose.yml up -d
```

### Verify Broker Health
```powershell
docker ps --filter "name=churnguard-kafka"
```
The container status should display `Up (healthy)`.

### Verify Topic Creation
```powershell
docker exec churnguard-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --if-not-exists --topic churn-customers --partitions 1 --replication-factor 1
docker exec churnguard-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
```

---

## 2. Run the Consumer and Producer

Open two PowerShell terminals from the project root.

### Terminal 1: Start the Consumer
Start the consumer first so it is listening before records arrive:

```powershell
# Ingest all 10,000 customer records and exit
python kafka\consumer.py --max-records 10000 --group churnguard-analytics
```

### Terminal 2: Stream Records via the Producer
```powershell
# Stream all 10,000 records at maximum speed
python kafka\producer.py --delay-ms 0

# Or simulate paced real-time streaming with a 25 ms delay per record
python kafka\producer.py --delay-ms 25
```

### Quick Connection Check (Sample of 20 Records)
```powershell
# Terminal 1:
python kafka\consumer.py --max-records 20 --group churnguard-test
# Terminal 2:
python kafka\producer.py --limit 20 --delay-ms 0
```

---

## 3. Verify Output Artifacts

Upon completion, the consumer generates:
- `results/streamed_customers.jsonl`: Line-delimited JSON stream of raw customer records.
- `results/stream_summary.json`: Aggregated metrics (total records consumed, historical churn count, market breakdown).

The Streamlit dashboard reads `results/stream_summary.json` to present the recorded streaming snapshot under **Kafka stream summary**.

---

## 4. Stop the Kafka Service

When finished with the demo:

```powershell
docker compose -f kafka/docker-compose.yml down
```
