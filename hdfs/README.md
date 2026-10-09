# HDFS landing and partitioned data

This stage prepares the historical customer CSV as country/churn partitions, then uploads the original CSV, partitions, and any generated Kafka stream output to a running HDFS cluster.

## 1. Prepare locally

From the project directory:

```powershell
python hdfs\prepare_data.py
```

This writes partitioned files and a manifest under `results\hdfs_ready\bank_customers`. It keeps the original CSV intact.

## 2. Start the local HDFS service

Docker Desktop must be running. From PowerShell, start the official Apache Hadoop 3.5.0 NameNode and DataNode services:

```powershell
docker compose -f "C:\Users\Hp\Documents\ChatGPT\chur\hdfs\docker-compose.yml" up -d
```

The NameNode dashboard is at `http://localhost:9870`. The uploader places the original CSV in `/churnguard/raw`, partition files in `/churnguard/curated/bank_customers`, and Kafka event/summary files (when present) in `/churnguard/raw/kafka`:

```powershell
python hdfs\upload_to_hdfs.py
```

Use `--hdfs-root /another/path` to choose a different destination. The uploader sends files through `docker compose exec`, so a local Hadoop CLI installation is not needed.

## 3. Analyze the HDFS partitions

After the NameNode and DataNode are running and the upload finishes, run this from the project folder:

```powershell
python hdfs\analyze_hdfs.py
```

The script reads each country/churn partition from HDFS, calculates customer and churn counts by country, and writes `results\hdfs_country_churn_summary.csv`. It reads the HDFS copies, not the local source CSV.

## 4. Run the aggregation as Hadoop MapReduce

The container includes Hadoop Streaming and Python 3. Run the mapper/reducer job from the project folder:

```powershell
python hdfs\run_mapreduce.py
```

This runs a real Hadoop Streaming job over the HDFS partition tree. Each run writes a new result directory under `/churnguard/analytics/` and saves a convenient local copy to `results\hdfs_mapreduce_country_summary.csv`.
