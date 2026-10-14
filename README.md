# ChurnGuard AI (PS 45 — Bank Customer Churn Prediction)

ChurnGuard AI is an end-to-end Big Data Analytics and Machine Learning project designed for **Problem Statement 45: Bank Customer Churn Prediction**.

Retail banks lose customers to competitors without early warning because churn is typically identified only after an account is closed. This project implements a complete big data ingestion, distributed storage, machine learning classification, and retention outreach workflow.

---

## Architecture

```text
Customer Dataset (CSV)
         │
         ▼
 Apache Kafka Producer ──► Kafka Topic (`churn-customers`) ──► Kafka Consumer
                                                                     │
                                                                     ▼
                                                             Apache Hadoop HDFS
                                                           (`/churnguard/curated`)
                                                                     │
                                                                     ▼
                                                         Hadoop Streaming MapReduce
                                                         (Country Churn Aggregation)
                                                                     │
                                                                     ▼
                                                            Retention Dashboard
                                                           (Streamlit UI + ML)
```

> **Data Pipeline Truth in Architecture:** The machine learning classification model trains on historical customer attributes from the source CSV (`data/Bank Customer Churn Prediction.csv`). Kafka streams customer transaction and demographic records into the analytics pipeline, which lands in Hadoop HDFS. Hadoop Streaming MapReduce executes distributed country-level risk aggregation across HDFS partitions. The Streamlit retention dashboard combines model scoring, retention outreach prioritization (>0.60 threshold), and verifiable pipeline artifacts.

---

## Official PS 45 Requirements & Implementation

| Requirement | Implementation in ChurnGuard AI | Status |
| :--- | :--- | :--- |
| **Kafka Ingestion** | `kafka/producer.py` & `kafka/consumer.py` on Apache Kafka (KRaft mode). Ingests 10,000 customer events to topic `churn-customers`. | Verified (10,000 records ingested) |
| **HDFS Storage** | Apache Hadoop 3.5.0 NameNode + DataNode cluster. `hdfs/upload_to_hdfs.py` stages raw and partitioned customer data. | Verified on live cluster |
| **MapReduce Aggregation** | Hadoop Streaming MapReduce (`hdfs/run_mapreduce.py`, `mapreduce_mapper.py`, `mapreduce_reducer.py`). | Verified on live cluster |
| **Classification ML** | Balanced Logistic Regression pipeline with median/modal imputation, standard scaling, and one-hot encoding (`src/train_model.py`). | Verified (0.777 ROC AUC, 70.0% Recall) |
| **Retention Flag (>0.60)** | Customers with predicted churn probability strictly greater than 0.60 (`churn_probability > 0.60`) flagged for retention outreach. Exactly 0.60 is NOT flagged. | Implemented & tested |
| **Retention Dashboard** | Interactive Streamlit application (`dashboard/app.py`) displaying portfolio risk, retention outreach targets, customer explorer, and CSV scoring. | Verified |

---

## Project Layout

```text
data/Bank Customer Churn Prediction.csv   Source dataset (10,000 customers, 12 features)
src/data_analysis.py                     Descriptive churn analytics and visual distributions
src/train_model.py                       Reproducible classification pipeline and evaluation
dashboard/app.py                         Interactive Streamlit retention dashboard
kafka/docker-compose.yml                 Apache Kafka in KRaft mode (port 9092)
kafka/producer.py                        Kafka customer event producer
kafka/consumer.py                        Kafka customer event consumer
kafka/README.md                          Kafka streaming instructions
hdfs/docker-compose.yml                  Apache Hadoop 3.5.0 cluster (NameNode + DataNode)
hdfs/config                              HDFS site XML properties
hdfs/prepare_data.py                     Country/churn partition staging
hdfs/upload_to_hdfs.py                   HDFS uploader
hdfs/analyze_hdfs.py                     HDFS partition reader & verification
hdfs/run_mapreduce.py                    Hadoop Streaming MapReduce execution script
hdfs/mapreduce_mapper.py                 Streaming mapper (country, count, churn)
hdfs/mapreduce_reducer.py                Streaming reducer (country aggregation)
hdfs/README.md                           Hadoop HDFS & MapReduce instructions
tests/test_retention_and_model.py        Automated test suite (pytest)
results/churn_model.joblib               Trained and serialized ML pipeline
results/model_metrics.json               Evaluation metrics on held-out test split
results/stream_summary.json              Recorded Kafka streaming event snapshot
results/hdfs_mapreduce_country_summary.csv Real MapReduce country aggregation output
```

---

## Setup & Prerequisites

### Prerequisites
- **Operating System:** Windows 10/11, macOS, or Linux.
- **Python:** Python 3.10 or newer.
- **Docker Desktop:** Running (WSL2 backend on Windows).

### 1. Environment Installation
In PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2. Run Automated Verification Tests
```powershell
python -m pytest tests/test_retention_and_model.py -v
```

---

## Execution Guide (Step-by-Step)

### Step 1: Model Training & Descriptive Analytics
```powershell
python src\data_analysis.py
python src\train_model.py
```

### Step 2: Live Kafka Streaming
Ensure Docker Desktop is active:

```powershell
# 1. Start the Kafka broker (KRaft mode)
docker compose -f kafka/docker-compose.yml up -d

# 2. Verify broker health
docker ps --filter "name=churnguard-kafka"

# 3. Create topic
docker exec churnguard-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --if-not-exists --topic churn-customers --partitions 1 --replication-factor 1

# 4. Start the consumer in Terminal 1 (listens for 10,000 records)
python kafka\consumer.py --max-records 10000 --group churnguard-analytics

# 5. In Terminal 2: Stream all records
python kafka\producer.py --delay-ms 0
```

### Step 3: Hadoop HDFS Storage & MapReduce
```powershell
# 1. Start Hadoop NameNode and DataNode
docker compose -f hdfs/docker-compose.yml up -d

# 2. Check cluster report
docker compose -f hdfs/docker-compose.yml exec -T namenode hdfs dfsadmin -report

# 3. Stage local partitions
python hdfs\prepare_data.py

# 4. Upload raw CSV, partitions, and Kafka artifacts to HDFS
python hdfs\upload_to_hdfs.py

# 5. Verify HDFS directory structure
docker compose -f hdfs/docker-compose.yml exec -T namenode hdfs dfs -ls -R /churnguard

# 6. Run Hadoop Streaming MapReduce country aggregation
python hdfs\run_mapreduce.py
```

### Step 4: Launch the Retention Dashboard
```powershell
streamlit run dashboard\app.py
```
Open `http://localhost:8501` in your browser.

### Shutdown Services
```powershell
docker compose -f kafka/docker-compose.yml down
docker compose -f hdfs/docker-compose.yml down
```

---

## 90-Day Prediction Target Limitation (Honest Disclosure)

The official problem statement mentions a 90-day churn forecast horizon. However:
- The dataset (`Bank Customer Churn Prediction.csv`) is a static cross-sectional table without timestamps, transaction history, or cohort tracking.
- The `churn` column represents historical binary attrition (`1 = left the bank, 0 = remained`).
- In strict adherence to academic and engineering ethics, **we do not fabricate dates, synthetic time-series, or fictitious future labels**.
- The classification model estimates the customer churn-risk probability based on historical profiles. This probability is directly mapped to the **>0.60 retention outreach threshold**, providing proactive actionable outreach candidates for bank retention teams.

---

## Troubleshooting

- **Port Conflicts (9092 or 9870):** Ensure no existing Kafka or Hadoop process occupies ports 9092 or 9870. Use `docker ps` to verify running containers.
- **NameNode Not Formatted Error:** If NameNode data volumes are cleared, the custom compose command in `hdfs/docker-compose.yml` automatically formats the filesystem on startup.
- **ModuleNotFoundError for Plotly / Kafka:** Ensure your active virtual environment has executed `pip install -r requirements.txt`.
