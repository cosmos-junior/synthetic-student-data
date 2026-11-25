"""Comparative evaluation of synthetic student data models.

Evaluates Gaussian Copula, CTGAN, and TVAE across three dimensions:
1. Statistical fidelity (SDMetrics QualityReport & DiagnosticReport)
2. Privacy risk (NewRowSynthesis, DCRBaselineProtection, DisclosureProtection)
3. Downstream ML utility (TRTR vs TSTR classification and regression)
"""

from pathlib import Path
import warnings

import numpy as np
import pandas as pd
from sdmetrics.reports import DiagnosticReport, QualityReport
from sdmetrics.single_table import (
    DCRBaselineProtection,
    DisclosureProtection,
    NewRowSynthesis,
)
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, f1_score, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.synthetic_data.configure_metadata import TABLE_NAME, configure_metadata


MODEL_FILES = {
    "Gaussian Copula": "gaussian_copula_synthetic.csv",
    "CTGAN": "ctgan_synthetic.csv",
    "TVAE": "tvae_synthetic.csv",
}

ML_NUMERIC_FEATURES = ["age", "year_of_study", "attendance_percentage", "coursework_score"]
ML_CATEGORICAL_FEATURES = ["gender", "programme"]
ML_FEATURES = ML_NUMERIC_FEATURES + ML_CATEGORICAL_FEATURES

QUASI_IDENTIFIERS = ["age", "gender", "programme", "year_of_study"]
SENSITIVE_COLUMNS = ["grade", "academic_status"]


def _build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), ML_NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), ML_CATEGORICAL_FEATURES),
        ]
    )


def evaluate_statistical_fidelity(
    real_data: pd.DataFrame,
    synthetic_data: pd.DataFrame,
    metadata_dict: dict,
) -> dict:
    """Compute SDMetrics QualityReport and DiagnosticReport scores."""

    real_tables = {TABLE_NAME: real_data}
    synth_tables = {TABLE_NAME: synthetic_data}

    quality_report = QualityReport()
    quality_report.generate(real_tables, synth_tables, metadata_dict, verbose=False)
    quality_props = quality_report.get_properties().set_index("Property")["Score"]

    diagnostic_report = DiagnosticReport()
    diagnostic_report.generate(real_tables, synth_tables, metadata_dict, verbose=False)
    diag_props = diagnostic_report.get_properties().set_index("Property")["Score"]

    return {
        "quality_overall": round(float(quality_report.get_score()), 4),
        "column_shapes": round(float(quality_props.get("Column Shapes", np.nan)), 4),
        "column_pair_trends": round(float(quality_props.get("Column Pair Trends", np.nan)), 4),
        "data_validity": round(float(diag_props.get("Data Validity", np.nan)), 4),
        "data_structure": round(float(diag_props.get("Data Structure", np.nan)), 4),
    }


def evaluate_privacy_risk(
    real_data: pd.DataFrame,
    synthetic_data: pd.DataFrame,
    metadata_dict: dict,
) -> dict:
    """Compute SDMetrics privacy protection metrics (higher = better protection)."""

    new_row_score = NewRowSynthesis.compute(
        real_data=real_data,
        synthetic_data=synthetic_data,
        metadata=metadata_dict,
        table_name=TABLE_NAME,
    )
    dcr_score = DCRBaselineProtection.compute(
        real_data=real_data,
        synthetic_data=synthetic_data,
        metadata=metadata_dict,
        table_name=TABLE_NAME,
    )
    disclosure_score = DisclosureProtection.compute(
        real_data=real_data,
        synthetic_data=synthetic_data,
        known_column_names=QUASI_IDENTIFIERS,
        sensitive_column_names=SENSITIVE_COLUMNS,
    )

    return {
        "new_row_synthesis": round(float(new_row_score), 4),
        "dcr_baseline_protection": round(float(dcr_score), 4),
        "disclosure_protection": round(float(disclosure_score), 4),
    }


def evaluate_ml_utility(
    train_data: pd.DataFrame,
    test_data: pd.DataFrame,
) -> dict:
    """Train classifiers and regressors on train_data and evaluate on held-out real test_data."""

    x_train = train_data[ML_FEATURES]
    x_test = test_data[ML_FEATURES]

    clf = Pipeline(
        [
            ("prep", _build_preprocessor()),
            ("model", RandomForestClassifier(n_estimators=200, random_state=42)),
        ]
    )
    clf.fit(x_train, train_data["academic_status"])
    status_preds = clf.predict(x_test)

    reg = Pipeline(
        [
            ("prep", _build_preprocessor()),
            ("model", RandomForestRegressor(n_estimators=200, random_state=42)),
        ]
    )
    reg.fit(x_train, train_data["final_score"])
    score_preds = reg.predict(x_test)

    rmse = float(np.sqrt(mean_squared_error(test_data["final_score"], score_preds)))
    return {
        "status_accuracy": round(float(accuracy_score(test_data["academic_status"], status_preds)), 4),
        "status_macro_f1": round(
            float(f1_score(test_data["academic_status"], status_preds, average="macro")), 4
        ),
        "final_score_r2": round(float(r2_score(test_data["final_score"], score_preds)), 4),
        "final_score_rmse": round(rmse, 4),
    }


def evaluate_all_models() -> pd.DataFrame:
    """Run statistical fidelity, privacy, and ML utility evaluation for all models."""

    project_root = Path(__file__).resolve().parents[2]
    real_file = project_root / "data" / "processed" / "student_training_data.csv"
    outputs_dir = project_root / "outputs"

    real_data = pd.read_csv(real_file)
    metadata_dict = configure_metadata().to_dict()

    real_train, real_test = train_test_split(
        real_data,
        test_size=0.2,
        random_state=42,
        stratify=real_data["academic_status"],
    )

    trtr_metrics = evaluate_ml_utility(real_train, real_test)
    rows = [
        {
            "model": "Real Baseline (TRTR)",
            "quality_overall": 1.0,
            "column_shapes": 1.0,
            "column_pair_trends": 1.0,
            "data_validity": 1.0,
            "data_structure": 1.0,
            "new_row_synthesis": np.nan,
            "dcr_baseline_protection": np.nan,
            "disclosure_protection": np.nan,
            **trtr_metrics,
        }
    ]

    for model_name, filename in MODEL_FILES.items():
        synth_path = outputs_dir / filename
        synth_df = pd.read_csv(synth_path)
        if "student_id" in synth_df.columns:
            synth_df = synth_df.drop(columns=["student_id"])

        fidelity = evaluate_statistical_fidelity(real_data, synth_df, metadata_dict)
        privacy = evaluate_privacy_risk(real_data, synth_df, metadata_dict)
        ml_utility = evaluate_ml_utility(synth_df, real_test)

        rows.append(
            {
                "model": model_name,
                **fidelity,
                **privacy,
                **ml_utility,
            }
        )

    summary_df = pd.DataFrame(rows)
    summary_path = outputs_dir / "evaluation_summary.csv"
    summary_df.to_csv(summary_path, index=False)

    print("\n========== COMPARATIVE EVALUATION SUMMARY ==========")
    print(summary_df.to_string(index=False))
    print(f"\nSaved evaluation summary to: {summary_path}")

    return summary_df


if __name__ == "__main__":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        evaluate_all_models()
