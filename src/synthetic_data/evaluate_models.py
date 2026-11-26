"""Comparative evaluation of synthetic tabular data models.

Evaluates Gaussian Copula, CTGAN, and TVAE across three dimensions:
1. Statistical fidelity (SDMetrics QualityReport & DiagnosticReport)
2. Privacy risk (SDMetrics + nearest-neighbor DCR, duplicate/near-duplicate, MIA indicator)
3. Leak-free downstream ML utility (TRTR vs TSTR across repeated splits)
"""

from pathlib import Path
from typing import Any
import warnings

import numpy as np
import pandas as pd
from sdmetrics.reports import DiagnosticReport, QualityReport
from sdmetrics.single_table import (
    DCRBaselineProtection,
    DisclosureProtection,
    NewRowSynthesis,
)
from sdv.single_table import (
    CTGANSynthesizer,
    GaussianCopulaSynthesizer,
    TVAESynthesizer,
)
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.synthetic_data.configure_metadata import TABLE_NAME, configure_metadata
from src.synthetic_data.generation_utils import (
    apply_student_post_processing,
    set_reproducible_seed,
)


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


def _build_preprocessor(
    numeric_features: list[str] | None = None,
    categorical_features: list[str] | None = None,
) -> ColumnTransformer:
    num_cols = numeric_features if numeric_features is not None else ML_NUMERIC_FEATURES
    cat_cols = categorical_features if categorical_features is not None else ML_CATEGORICAL_FEATURES
    transformers = []
    if num_cols:
        transformers.append(("num", StandardScaler(), num_cols))
    if cat_cols:
        transformers.append(("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols))
    return ColumnTransformer(transformers=transformers)


def evaluate_statistical_fidelity(
    real_data: pd.DataFrame,
    synthetic_data: pd.DataFrame,
    metadata_dict: dict,
    table_name: str = TABLE_NAME,
) -> dict[str, float]:
    """Compute SDMetrics QualityReport and DiagnosticReport scores."""

    real_tables = {table_name: real_data}
    synth_tables = {table_name: synthetic_data}

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


def _compute_nn_distances(reference_df: pd.DataFrame, query_df: pd.DataFrame) -> np.ndarray:
    """Compute standardized Euclidean nearest-neighbor distances from query_df to reference_df."""
    num_cols = [c for c in reference_df.columns if pd.api.types.is_numeric_dtype(reference_df[c])]
    cat_cols = [c for c in reference_df.columns if c not in num_cols]

    preprocessor = _build_preprocessor(num_cols, cat_cols)
    ref_clean = reference_df.copy()
    qry_clean = query_df.copy()
    for c in num_cols:
        median_val = float(ref_clean[c].median()) if ref_clean[c].notna().any() else 0.0
        ref_clean[c] = ref_clean[c].fillna(median_val)
        qry_clean[c] = qry_clean[c].fillna(median_val)
    for c in cat_cols:
        ref_clean[c] = ref_clean[c].fillna("MISSING").astype(str)
        qry_clean[c] = qry_clean[c].fillna("MISSING").astype(str)

    ref_mat = preprocessor.fit_transform(ref_clean)
    qry_mat = preprocessor.transform(qry_clean)
    nn = NearestNeighbors(n_neighbors=1, metric="euclidean")
    nn.fit(ref_mat)
    distances, _ = nn.kneighbors(qry_mat)
    return distances.ravel()


def classify_privacy_risk(
    dcr_baseline_protection: float | None,
    exact_duplicate_rate: float,
    near_duplicate_rate: float,
) -> str:
    """Assign an explicit empirical risk band based on observed privacy indicators."""
    if exact_duplicate_rate > 0.01 or near_duplicate_rate > 0.05 or (
        dcr_baseline_protection is not None and dcr_baseline_protection < 0.15
    ):
        return "Elevated observed risk"
    if (dcr_baseline_protection is not None and dcr_baseline_protection < 0.35) or near_duplicate_rate > 0.01:
        return "Moderate observed risk"
    return "Low observed risk"


def evaluate_privacy_risk(
    real_data: pd.DataFrame,
    synthetic_data: pd.DataFrame,
    metadata_dict: dict,
    table_name: str = TABLE_NAME,
    known_columns: list[str] | None = None,
    sensitive_columns: list[str] | None = None,
    holdout_data: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Compute SDMetrics privacy indicators, nearest-neighbor DCR, and duplicate rates.

    Note: These are empirical privacy-risk indicators, not formal differential privacy guarantees.
    """
    new_row_score = NewRowSynthesis.compute(
        real_data=real_data,
        synthetic_data=synthetic_data,
        metadata=metadata_dict,
        table_name=table_name,
    )
    dcr_score = DCRBaselineProtection.compute(
        real_data=real_data,
        synthetic_data=synthetic_data,
        metadata=metadata_dict,
        table_name=table_name,
    )

    known_cols = [c for c in (known_columns or QUASI_IDENTIFIERS) if c in real_data.columns]
    sens_cols = [c for c in (sensitive_columns or SENSITIVE_COLUMNS) if c in real_data.columns]
    if known_cols and sens_cols:
        disclosure_score = float(
            DisclosureProtection.compute(
                real_data=real_data,
                synthetic_data=synthetic_data,
                known_column_names=known_cols,
                sensitive_column_names=sens_cols,
            )
        )
    else:
        disclosure_score = None

    common_cols = [c for c in real_data.columns if c in synthetic_data.columns]
    nn_distances = _compute_nn_distances(real_data[common_cols], synthetic_data[common_cols])
    exact_dup_rate = float(np.mean(nn_distances <= 1e-6))
    near_dup_rate = float(np.mean(nn_distances <= 0.05))

    mia_risk = None
    if holdout_data is not None and len(holdout_data) > 0:
        holdout_distances = _compute_nn_distances(synthetic_data[common_cols], holdout_data[common_cols])
        train_to_synth = _compute_nn_distances(synthetic_data[common_cols], real_data[common_cols])
        threshold = float(np.percentile(holdout_distances, 10))
        mia_risk = round(float(np.mean(train_to_synth <= threshold)), 4)

    dcr_val = round(float(dcr_score), 4)
    risk_band = classify_privacy_risk(dcr_val, exact_dup_rate, near_dup_rate)

    return {
        "new_row_synthesis": round(float(new_row_score), 4),
        "dcr_baseline_protection": dcr_val,
        "disclosure_protection": round(disclosure_score, 4) if disclosure_score is not None else None,
        "dcr_mean": round(float(np.mean(nn_distances)), 4),
        "dcr_min": round(float(np.min(nn_distances)), 4),
        "dcr_p05": round(float(np.percentile(nn_distances, 5)), 4),
        "exact_duplicate_rate": round(exact_dup_rate, 4),
        "near_duplicate_rate": round(near_dup_rate, 4),
        "membership_inference_risk": mia_risk,
        "privacy_risk_label": risk_band,
    }


def evaluate_ml_utility(
    train_data: pd.DataFrame,
    test_data: pd.DataFrame,
    target_column: str = "academic_status",
    regression_target: str | None = "final_score",
    features: list[str] | None = None,
) -> dict[str, float]:
    """Train classifiers/regressors on train_data and evaluate on held-out real test_data."""

    feat_cols = features or [c for c in ML_FEATURES if c in train_data.columns]
    num_cols = [c for c in feat_cols if pd.api.types.is_numeric_dtype(train_data[c])]
    cat_cols = [c for c in feat_cols if c not in num_cols]

    x_train = train_data[feat_cols]
    x_test = test_data[feat_cols]

    metrics: dict[str, float] = {}

    if target_column in train_data.columns and train_data[target_column].nunique() >= 2:
        clf = Pipeline(
            [
                ("prep", _build_preprocessor(num_cols, cat_cols)),
                ("model", RandomForestClassifier(n_estimators=150, random_state=42)),
            ]
        )
        clf.fit(x_train, train_data[target_column])
        preds = clf.predict(x_test)

        metrics["status_accuracy"] = round(float(accuracy_score(test_data[target_column], preds)), 4)
        metrics["status_precision"] = round(
            float(precision_score(test_data[target_column], preds, average="macro", zero_division=0)), 4
        )
        metrics["status_recall"] = round(
            float(recall_score(test_data[target_column], preds, average="macro", zero_division=0)), 4
        )
        metrics["status_macro_f1"] = round(
            float(f1_score(test_data[target_column], preds, average="macro", zero_division=0)), 4
        )
        if train_data[target_column].nunique() == 2 and hasattr(clf, "predict_proba"):
            pos_label = sorted(train_data[target_column].unique())[-1]
            probs = clf.predict_proba(x_test)[:, list(clf.classes_).index(pos_label)]
            y_true_bin = (test_data[target_column] == pos_label).astype(int)
            if len(np.unique(y_true_bin)) == 2:
                metrics["status_roc_auc"] = round(float(roc_auc_score(y_true_bin, probs)), 4)

        lr_clf = Pipeline(
            [
                ("prep", _build_preprocessor(num_cols, cat_cols)),
                ("model", LogisticRegression(max_iter=500, random_state=42)),
            ]
        )
        lr_clf.fit(x_train, train_data[target_column])
        lr_preds = lr_clf.predict(x_test)
        metrics["logreg_macro_f1"] = round(
            float(f1_score(test_data[target_column], lr_preds, average="macro", zero_division=0)), 4
        )

    if regression_target and regression_target in train_data.columns:
        reg = Pipeline(
            [
                ("prep", _build_preprocessor(num_cols, cat_cols)),
                ("model", RandomForestRegressor(n_estimators=150, random_state=42)),
            ]
        )
        reg.fit(x_train, train_data[regression_target])
        score_preds = reg.predict(x_test)
        rmse = float(np.sqrt(mean_squared_error(test_data[regression_target], score_preds)))
        metrics["final_score_mae"] = round(
            float(mean_absolute_error(test_data[regression_target], score_preds)), 4
        )
        metrics["final_score_rmse"] = round(rmse, 4)
        metrics["final_score_r2"] = round(float(r2_score(test_data[regression_target], score_preds)), 4)

        ridge = Pipeline(
            [
                ("prep", _build_preprocessor(num_cols, cat_cols)),
                ("model", Ridge(random_state=42)),
            ]
        )
        ridge.fit(x_train, train_data[regression_target])
        ridge_preds = ridge.predict(x_test)
        metrics["ridge_r2"] = round(float(r2_score(test_data[regression_target], ridge_preds)), 4)

    return metrics


def _make_synthesizer(model_name: str, metadata, epochs: int = 150, batch_size: int = 200):
    if model_name == "Gaussian Copula":
        return GaussianCopulaSynthesizer(metadata, enforce_min_max_values=True, enforce_rounding=True)
    if model_name == "CTGAN":
        return CTGANSynthesizer(
            metadata, enforce_min_max_values=True, enforce_rounding=True,
            epochs=epochs, batch_size=batch_size, verbose=False,
        )
    if model_name == "TVAE":
        return TVAESynthesizer(
            metadata, enforce_min_max_values=True, enforce_rounding=True,
            epochs=epochs, batch_size=batch_size, verbose=False,
        )
    raise ValueError(f"Unknown model: {model_name}")


def evaluate_all_models(seeds: tuple[int, ...] = (42, 7)) -> pd.DataFrame:
    """Run leak-free comparative evaluation across fidelity, privacy, and repeated-split ML utility."""

    project_root = Path(__file__).resolve().parents[2]
    real_file = project_root / "data" / "processed" / "student_training_data.csv"
    outputs_dir = project_root / "outputs"

    real_data = pd.read_csv(real_file)
    metadata = configure_metadata()
    metadata_dict = metadata.to_dict()

    # 1. Leak-free TRTR baseline across repeated splits
    trtr_runs = []
    for seed in seeds:
        r_train, r_test = train_test_split(
            real_data, test_size=0.2, random_state=seed, stratify=real_data["academic_status"]
        )
        trtr_runs.append(evaluate_ml_utility(r_train, r_test))

    trtr_mean = pd.DataFrame(trtr_runs).mean().round(4).to_dict()
    trtr_std = pd.DataFrame(trtr_runs).std().fillna(0).round(4).to_dict()

    rows: list[dict[str, Any]] = [
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
            "dcr_mean": np.nan,
            "dcr_min": np.nan,
            "dcr_p05": np.nan,
            "exact_duplicate_rate": np.nan,
            "near_duplicate_rate": np.nan,
            "membership_inference_risk": np.nan,
            "privacy_risk_label": "Reference Real Data",
            **trtr_mean,
            "status_macro_f1_std": trtr_std.get("status_macro_f1", 0.0),
            "final_score_r2_std": trtr_std.get("final_score_r2", 0.0),
        }
    ]

    for model_name, filename in MODEL_FILES.items():
        synth_path = outputs_dir / filename
        synth_df = pd.read_csv(synth_path)
        if "student_id" in synth_df.columns:
            synth_df = synth_df.drop(columns=["student_id"])

        fidelity = evaluate_statistical_fidelity(real_data, synth_df, metadata_dict)

        # Leak-free TSTR & holdout-aware privacy across repeated splits
        tstr_runs = []
        holdout_ref = None
        train_ref = None
        synth_split_ref = None
        for seed in seeds:
            set_reproducible_seed(seed)
            r_train, r_test = train_test_split(
                real_data, test_size=0.2, random_state=seed, stratify=real_data["academic_status"]
            )
            synth = _make_synthesizer(model_name, metadata)
            synth.fit({TABLE_NAME: r_train})
            sampled = synth.sample(num_rows=len(r_train))
            split_synth_df = sampled[TABLE_NAME] if isinstance(sampled, dict) else sampled
            split_synth_df = apply_student_post_processing(split_synth_df)
            tstr_runs.append(evaluate_ml_utility(split_synth_df, r_test))
            if seed == seeds[0]:
                train_ref, holdout_ref, synth_split_ref = r_train, r_test, split_synth_df

        privacy = evaluate_privacy_risk(
            train_ref if train_ref is not None else real_data,
            synth_split_ref if synth_split_ref is not None else synth_df,
            metadata_dict,
            holdout_data=holdout_ref,
        )
        tstr_mean = pd.DataFrame(tstr_runs).mean().round(4).to_dict()
        tstr_std = pd.DataFrame(tstr_runs).std().fillna(0).round(4).to_dict()

        rows.append(
            {
                "model": model_name,
                **fidelity,
                **privacy,
                **tstr_mean,
                "status_macro_f1_std": tstr_std.get("status_macro_f1", 0.0),
                "final_score_r2_std": tstr_std.get("final_score_r2", 0.0),
            }
        )

    summary_df = pd.DataFrame(rows)
    summary_path = outputs_dir / "evaluation_summary.csv"
    summary_df.to_csv(summary_path, index=False)

    print("\n========== LEAK-FREE COMPARATIVE EVALUATION SUMMARY ==========")
    print(summary_df.to_string(index=False))
    print(f"\nSaved evaluation summary to: {summary_path}")

    return summary_df


if __name__ == "__main__":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        evaluate_all_models()
