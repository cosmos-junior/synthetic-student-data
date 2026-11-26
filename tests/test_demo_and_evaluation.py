"""Unit tests for demo data generation and ML utility evaluation."""

import pandas as pd
import pytest

from src.synthetic_data.evaluate_models import evaluate_ml_utility
from src.synthetic_data.generate_demo_data import generate_demo_data
from src.synthetic_data.schema import REQUIRED_COLUMNS
from src.synthetic_data.validation import validate_student_data


def test_generate_demo_data_valid_and_reproducible():
    df1 = generate_demo_data(number_of_students=30, random_seed=7)
    df2 = generate_demo_data(number_of_students=30, random_seed=7)

    assert len(df1) == 30
    assert set(df1.columns) == set(REQUIRED_COLUMNS)
    assert validate_student_data(df1) == []
    pd.testing.assert_frame_equal(df1, df2)


def test_generate_demo_data_rejects_non_positive_count():
    with pytest.raises(ValueError):
        generate_demo_data(number_of_students=0)


def test_evaluate_ml_utility_returns_expected_metrics():
    train_df = generate_demo_data(number_of_students=60, random_seed=1)
    test_df = generate_demo_data(number_of_students=20, random_seed=2)

    metrics = evaluate_ml_utility(train_df, test_df)

    expected_keys = {
        "status_accuracy",
        "status_precision",
        "status_recall",
        "status_macro_f1",
        "final_score_mae",
        "final_score_rmse",
        "final_score_r2",
    }
    assert expected_keys.issubset(metrics.keys())
    assert 0.0 <= metrics["status_accuracy"] <= 1.0
    assert 0.0 <= metrics["status_macro_f1"] <= 1.0
    assert metrics["final_score_rmse"] >= 0.0
