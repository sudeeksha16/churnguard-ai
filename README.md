# ChurnGuard AI

A local bank customer churn analytics project built around the 10,000-row dataset in `data/`. It explores churn patterns, trains a reusable churn-risk model, and provides an interactive dashboard for reviewing customers and scoring uploaded records.

## Project layout

```text
data/Bank Customer Churn Prediction.csv   source data
src/data_analysis.py                     descriptive analytics and charts
src/train_model.py                       model training and evaluation
dashboard/app.py                         interactive Streamlit dashboard
kafka/producer.py                        CSV-to-Kafka event producer
kafka/consumer.py                        Kafka event consumer and summary
hdfs/prepare_data.py                     country/churn partitioned data staging
hdfs/upload_to_hdfs.py                   optional HDFS uploader
hdfs/analyze_hdfs.py                     country-level aggregation from HDFS partitions
hdfs/run_mapreduce.py                    Hadoop Streaming MapReduce country aggregation
results/                                 generated reports and model artifacts
```

`customer_id` is retained for customer lookup but excluded from training. `churn` is the historical binary target (1 = churned, 0 = stayed). This dataset does not define an outcome horizon, so scores are risk probabilities based on its historical labels, not validated 90-day forecasts.

## Setup (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python src\data_analysis.py
python src\train_model.py
streamlit run dashboard\app.py
```

The dashboard reads the project CSV and generated results. To score another file, upload a CSV with the same feature columns; `customer_id` and `churn` are optional.

## Kafka streaming demo

Start a Kafka broker, then follow [kafka/README.md](kafka/README.md) to stream customer records and save a local event snapshot. The demo streams the dataset's historical labels; it does not simulate live customer activity.

## HDFS data lake stage

Prepare local country/churn partitions with `python hdfs\prepare_data.py`, start the local Apache Hadoop HDFS containers with the steps in [hdfs/README.md](hdfs/README.md), upload them with `python hdfs\upload_to_hdfs.py`, then aggregate the HDFS partitions with `python hdfs\run_mapreduce.py`.

## Deploy the dashboard online

The Streamlit dashboard can be deployed without a running Kafka broker or HDFS cluster. It displays the saved stream and MapReduce summaries included in `results/`. The trained model, metrics, stream summary, and MapReduce CSV are intentionally included as app data. The raw dataset contains customer attributes, so use a **private GitHub repository** and restrict access to people you trust.

1. Create a private GitHub repository and push this project to it. Include `data/Bank Customer Churn Prediction.csv` and the four dashboard artifacts listed above.
2. Sign in at [Streamlit Community Cloud](https://share.streamlit.io/) with GitHub and grant access to the repository.
3. Choose **Create app**, select the repository's default branch, and set the app file path to `dashboard/app.py`.
4. Deploy. Community Cloud installs packages from the root `requirements.txt`; the app URL will be on `streamlit.app`.

Community Cloud deploys from GitHub, and repository files required by the app must be present there. See the [official deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) and [dependency guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies).

## Dataset

The checked-in CSV is the dataset selected in the project walkthrough. It contains 10,000 records, 12 columns, and no missing values. Keep the original source unchanged; analysis and model outputs are written under `results/`.
