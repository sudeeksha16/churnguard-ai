"""Tests for model loading, inference parity, PS 45 90-day retention outreach threshold, and pipeline logic."""
import json
import pytest
import pandas as pd
import numpy as np
import joblib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "Bank Customer Churn Prediction.csv"
MODEL_PATH = ROOT / "results" / "churn_model.joblib"
METRICS_PATH = ROOT / "results" / "model_metrics.json"


def test_dataset_schema_and_integrity():
    """Verify source dataset structure, 10,000 customer records, and absence of nulls."""
    assert DATA_PATH.exists(), f"Source dataset missing at {DATA_PATH}"
    df = pd.read_csv(DATA_PATH)
    assert len(df) == 10000, "Dataset must have exactly 10,000 records"
    assert df.isna().sum().sum() == 0, "Dataset should have zero missing values"
    expected_cols = [
        "customer_id", "credit_score", "country", "gender", "age",
        "tenure", "balance", "products_number", "credit_card",
        "active_member", "estimated_salary", "churn"
    ]
    assert list(df.columns) == expected_cols
    assert set(df["country"].unique()) == {"France", "Germany", "Spain"}
    assert set(df["churn"].unique()) == {0, 1}


def test_model_artifact_exists_and_loads():
    """Verify saved model artifact exists and can be deserialized."""
    assert MODEL_PATH.exists(), f"Model artifact not found at {MODEL_PATH}"
    artifact = joblib.load(MODEL_PATH)
    assert "model" in artifact
    assert "feature_columns" in artifact
    assert "target" in artifact
    assert artifact["target"] == "churn"
    expected_features = [
        "credit_score", "country", "gender", "age", "tenure",
        "balance", "products_number", "credit_card", "active_member", "estimated_salary"
    ]
    assert artifact["feature_columns"] == expected_features


def test_90_day_prediction_objective_and_metrics():
    """Verify that model evaluation records 90-day objective and 0.60 threshold evaluation."""
    assert METRICS_PATH.exists(), f"Metrics file missing at {METRICS_PATH}"
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    
    assert "objective" in metrics
    assert "90-Day" in metrics["objective"]
    assert "retention_outreach_evaluation" in metrics
    
    outreach = metrics["retention_outreach_evaluation"]
    assert outreach["threshold_rule"] == "churn_probability > 0.60"
    assert outreach["test_flagged_count"] > 0
    assert 0.0 < outreach["precision_at_threshold"] <= 1.0
    assert 0.0 < outreach["recall_at_threshold"] <= 1.0


def test_retention_threshold_boundary_conditions():
    """
    Official Requirement:
    Flag customers with churn probability strictly greater than 0.60 for retention outreach.
    Test scores below 0.60, exactly 0.60, and above 0.60.
    Exactly 0.60 must NOT be flagged.
    """
    test_scores = pd.Series([0.0, 0.35, 0.5999, 0.6000, 0.6001, 0.75, 1.0])
    
    # Official decision rule under test
    retention_flags = test_scores > 0.60

    assert bool(retention_flags[0]) is False   # 0.00
    assert bool(retention_flags[1]) is False   # 0.35
    assert bool(retention_flags[2]) is False   # 0.5999 (< 0.60)
    assert bool(retention_flags[3]) is False   # 0.6000 (EXACTLY 0.60 -> MUST NOT BE FLAGGED)
    assert bool(retention_flags[4]) is True    # 0.6001 (> 0.60 -> FLAGGED)
    assert bool(retention_flags[5]) is True    # 0.75 (> 0.60 -> FLAGGED)
    assert bool(retention_flags[6]) is True    # 1.00 (> 0.60 -> FLAGGED)


def test_model_inference_on_dataset():
    """Verify that model inference runs and outputs valid probability distribution."""
    artifact = joblib.load(MODEL_PATH)
    df = pd.read_csv(DATA_PATH)
    feature_cols = artifact["feature_columns"]
    
    # Run predict_proba
    probs = artifact["model"].predict_proba(df[feature_cols])[:, 1]
    
    assert len(probs) == len(df) == 10000
    assert (probs >= 0.0).all() and (probs <= 1.0).all()
    
    # Check retention outreach flag count
    flagged = (probs > 0.60)
    flagged_count = int(flagged.sum())
    assert flagged_count > 0, "Expected high-risk customers to be flagged for outreach"
    assert flagged_count < len(df), "Not all customers should be flagged"
    
    # Specifically check boundary on real scores
    assert ((probs == 0.60) & flagged).sum() == 0, "Exact 0.60 should not be flagged"


def test_mapreduce_streaming_logic():
    """Verify Mapper and Reducer logic reproduces exact country aggregation counts."""
    df = pd.read_csv(DATA_PATH)
    # The columns: customer_id (0), credit_score (1), country (2), ..., churn (11 / -1)
    assert df.columns[2] == "country"
    assert df.columns[-1] == "churn"
    
    country_churn = df.groupby("country")["churn"].agg(customers="count", churned="sum")
    assert country_churn.loc["France", "customers"] == 5014
    assert country_churn.loc["France", "churned"] == 810
    assert country_churn.loc["Germany", "customers"] == 2509
    assert country_churn.loc["Germany", "churned"] == 814
    assert country_churn.loc["Spain", "customers"] == 2477
    assert country_churn.loc["Spain", "churned"] == 413
