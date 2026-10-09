"""Create descriptive churn summaries and chart artifacts."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "Bank Customer Churn Prediction.csv"
RESULTS = ROOT / "results"


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    df = pd.read_csv(DATA_PATH)
    if "churn" not in df or not set(df["churn"].dropna().unique()).issubset({0, 1}):
        raise ValueError("Expected a binary 'churn' target with values 0 and 1.")

    summary = {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "churned": int(df["churn"].sum()),
        "retained": int((df["churn"] == 0).sum()),
        "churn_rate": float(df["churn"].mean()),
        "missing_values": {str(k): int(v) for k, v in df.isna().sum().items()},
        "churn_rate_by_country": df.groupby("country", observed=True)["churn"].mean().sort_values(ascending=False).round(4).to_dict(),
        "churn_rate_by_gender": df.groupby("gender", observed=True)["churn"].mean().round(4).to_dict(),
        "churn_rate_by_active_member": df.groupby("active_member", observed=True)["churn"].mean().round(4).to_dict(),
        "average_age_by_churn": {str(k): round(float(v), 2) for k, v in df.groupby("churn")["age"].mean().items()},
    }
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    df.groupby(["country", "churn"]).size().unstack(fill_value=0).to_csv(RESULTS / "country_churn_counts.csv")

    sns.set_theme(style="whitegrid", palette=["#b7f36b", "#ff786b"])
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    sns.countplot(data=df, x="churn", ax=axes[0])
    axes[0].set(title="Customer outcomes", xlabel="Churn (0 = stayed, 1 = churned)", ylabel="Customers")
    sns.barplot(data=df, x="country", y="churn", errorbar=None, ax=axes[1])
    axes[1].set(title="Churn rate by country", xlabel="", ylabel="Churn rate")
    sns.histplot(data=df, x="age", hue="churn", bins=24, stat="density", common_norm=False, element="step", ax=axes[2])
    axes[2].set(title="Age distribution", xlabel="Age", ylabel="Density")
    fig.tight_layout()
    fig.savefig(RESULTS / "churn_overview.png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"Analyzed {len(df):,} customers; churn rate {summary['churn_rate']:.1%}.")
    print(f"Wrote summary and chart files to {RESULTS}")


if __name__ == "__main__":
    main()
