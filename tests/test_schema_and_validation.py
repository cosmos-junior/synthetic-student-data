"""Unit tests for schema helpers and dataset validation."""

import pandas as pd
import pytest

from src.synthetic_data.schema import (
    COURSEWORK_WEIGHT,
    EXAM_WEIGHT,
    REQUIRED_COLUMNS,
    determine_grade,
    determine_status,
)
from src.synthetic_data.validation import validate_student_data


def _make_valid_df() -> pd.DataFrame:
    rows = [
        {
            "student_id": "IN1700001",
            "age": 20,
            "gender": "Male",
            "programme": "BIT",
            "year_of_study": 2,
            "attendance_percentage": 85.0,
            "coursework_score": 70.0,
            "exam_score": 80.0,
        },
        {
            "student_id": "IN1700002",
            "age": 22,
            "gender": "Female",
            "programme": "BCS",
            "year_of_study": 3,
            "attendance_percentage": 62.5,
            "coursework_score": 30.0,
            "exam_score": 35.0,
        },
    ]
    for row in rows:
        final = round(row["coursework_score"] * COURSEWORK_WEIGHT + row["exam_score"] * EXAM_WEIGHT, 2)
        row["final_score"] = final
        row["grade"] = determine_grade(final)
        row["academic_status"] = determine_status(final)
    return pd.DataFrame(rows)


@pytest.mark.parametrize(
    "score, expected_grade, expected_status",
    [
        (70.0, "A", "Pass"),
        (60.0, "B", "Pass"),
        (50.0, "C", "Pass"),
        (40.0, "D", "Pass"),
        (39.99, "E", "Fail"),
    ],
)
def test_grade_and_status_boundaries(score, expected_grade, expected_status):
    assert determine_grade(score) == expected_grade
    assert determine_status(score) == expected_status


def test_valid_dataset_passes():
    df = _make_valid_df()
    assert set(df.columns) == set(REQUIRED_COLUMNS)
    assert validate_student_data(df) == []


def test_missing_columns_reported():
    df = _make_valid_df().drop(columns=["grade"])
    errors = validate_student_data(df)
    assert any("Missing columns" in err for err in errors)


def test_empty_dataset_reported():
    df = _make_valid_df().iloc[0:0]
    errors = validate_student_data(df)
    assert "Dataset is empty." in errors


def test_duplicate_student_id_reported():
    df = _make_valid_df()
    df.loc[1, "student_id"] = df.loc[0, "student_id"]
    errors = validate_student_data(df)
    assert "Student IDs must be unique." in errors


def test_out_of_range_and_non_integer_reported():
    df = _make_valid_df()
    df["age"] = df["age"].astype(float)
    df.loc[0, "age"] = 15.5
    errors = validate_student_data(df)
    assert any("age must be between" in err for err in errors)
    assert any("age must contain whole numbers" in err for err in errors)


def test_invalid_category_reported():
    df = _make_valid_df()
    df.loc[0, "programme"] = "INVALID"
    errors = validate_student_data(df)
    assert any("programme contains invalid categories." in err for err in errors)


def test_derived_formula_and_label_mismatches_reported():
    df = _make_valid_df()
    df.loc[0, "final_score"] = 50.0
    df.loc[0, "grade"] = "E"
    df.loc[0, "academic_status"] = "Fail"
    errors = validate_student_data(df)
    assert "Final scores do not follow the weighted formula." in errors
    assert "Grades do not match final scores." in errors
    assert "Academic status does not match final scores." in errors
