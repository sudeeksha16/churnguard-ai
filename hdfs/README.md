# Hadoop HDFS Storage & MapReduce Aggregation

This stage fulfills the official PS 45 objective: **Store customer account and transaction activity on Hadoop HDFS, and execute scalable distributed aggregation via Hadoop Streaming MapReduce**.

---

## 1. Prepare Partitioned Data Locally

From the project root directory:

```powershell
python hdfs\prepare_data.py
```

This partitions the 10,000 customer records by `country` and historical `churn` label into Hive-style directory structures (`country=.../churn=.../part-00000.csv`) under `results\hdfs_ready\bank_customers`, along with a `manifest.json`. The original CSV remains untouched.

---

## 2. Start the Local Apache Hadoop 3.5.0 Cluster

Docker Desktop must be running. Start the NameNode and DataNode containers:

```powershell
docker compose -f hdfs/docker-compose.yml up -d
```

> **Note on Initial Setup:** The NameNode container is configured to automatically format its file system (`hdfs namenode -format -force`) on its initial startup if an unformatted volume is detected.

### Verify Cluster Health & Active DataNodes
```powershell
docker compose -f hdfs/docker-compose.yml exec -T namenode hdfs dfsadmin -report
```
The report should confirm **1 Live datanode** in `Normal` status. The NameNode Web UI is accessible at `http://localhost:9870`.

---

## 3. Upload Data to HDFS

Upload the raw CSV dataset, the partitioned dataset tree, and any Kafka streaming output (`results/streamed_customers.jsonl` and `results/stream_summary.json`) into HDFS:

```powershell
python hdfs\upload_to_hdfs.py
```

### Verify HDFS File System Hierarchy
```powershell
docker compose -f hdfs/docker-compose.yml exec -T namenode hdfs dfs -ls -R /churnguard
```
This lists:
- `/churnguard/raw/`: Original dataset CSV and Kafka streaming logs.
- `/churnguard/curated/bank_customers/`: 6 partitioned CSV files across France, Germany, and Spain.

---

## 4. Run Hadoop Streaming MapReduce

Execute the distributed MapReduce country-level churn aggregation job:

```powershell
python hdfs\run_mapreduce.py
```

This sends `hdfs/mapreduce_mapper.py` and `hdfs/mapreduce_reducer.py` into the Hadoop cluster via `hadoop-streaming-3.5.0.jar`. It recursively processes all HDFS partitions and outputs country churn summaries:
- **France:** 5,014 records (810 churned, 16.15% churn rate)
- **Germany:** 2,509 records (814 churned, 32.44% churn rate)
- **Spain:** 2,477 records (413 churned, 16.67% churn rate)
- **Total:** 10,000 records (2,037 churned, 20.37% churn rate)

Results are committed to HDFS under `/churnguard/analytics/` and a local copy is saved to `results/hdfs_mapreduce_country_summary.csv`.

---

## 5. Alternative: Direct Partition Verification

To read and summarize each partition from HDFS without Hadoop Streaming:

```powershell
python hdfs\analyze_hdfs.py
```

---

## 6. Stop the Hadoop Cluster

When finished:

```powershell
docker compose -f hdfs/docker-compose.yml down
```
