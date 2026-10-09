"""Train and evaluate a reproducible churn-risk classifier."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, classification_report,
                             confusion_matrix, precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "Bank Customer Churn Prediction.csv"
RESULTS = ROOT / "results"
TARGET = "churn"
DROP = ["customer_id", TARGET]


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    df = pd.read_csv(DATA_PATH)
    if TARGET not in df:
        raise ValueError(f"Missing target column: {TARGET}")
    X, y = df.drop(columns=DROP, errors="ignore"), df[TARGET].astype(int)
    categorical = X.select_dtypes(include=["object", "category"]).columns.tolist()
    numeric = X.select_dtypes(exclude=["object", "category"]).columns.tolist()
    prep = ColumnTransformer([
        ("numeric", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric),
        ("categorical", Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                                  ("encode", OneHotEncoder(handle_unknown="ignore"))]), categorical),
    ])
    model = Pipeline([("prepare", prep), ("classifier", LogisticRegression(max_iter=1500, class_weight="balanced", random_state=42))])
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    model.fit(X_train, y_train)
    predicted = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]
    metrics = {
        "model": "Logistic Regression (balanced class weights)",
        "target": TARGET,
        "excluded_columns": ["customer_id"],
        "train_rows": int(len(X_train)), "test_rows": int(len(X_test)),
        "test_churn_rate": float(y_test.mean()),
        "accuracy": float(accuracy_score(y_test, predicted)),
        "precision_churn": float(precision_score(y_test, predicted, zero_division=0)),
        "recall_churn": float(recall_score(y_test, predicted, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "average_precision": float(average_precision_score(y_test, probabilities)),
        "confusion_matrix_labels_0_1": confusion_matrix(y_test, predicted, labels=[0, 1]).tolist(),
        "classification_report": classification_report(y_test, predicted, output_dict=True, zero_division=0),
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "caveat": "Historical churn-risk probability; dataset does not define a forecast horizon.",
    }
    joblib.dump({"model": model, "feature_columns": list(X.columns), "target": TARGET}, RESULTS / "churn_model.joblib")
    (RESULTS / "model_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"ROC AUC: {metrics['roc_auc']:.3f} | churn recall: {metrics['recall_churn']:.3f}")
    print(f"Saved model and metrics to {RESULTS}")


if __name__ == "__main__":
    main()
