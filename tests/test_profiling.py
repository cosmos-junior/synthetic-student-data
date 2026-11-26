"""Unit tests for CSV upload validation, sanitization, profiling, and SDV metadata."""

import pandas as pd
import pytest

from src.synthetic_data.generate_demo_data import generate_demo_data
from src.synthetic_data.profiling import (
    build_sdv_metadata,
    profile_dataframe,
    sanitize_dataframe_for_export,
    validate_uploaded_csv,
)


def test_sanitize_dataframe_for_export_neutralizes_formula_injection():
    df = pd.DataFrame(
        {
            "name": ["=cmd|' /C calc'!A0", "+1+1", "-2+3", "@SUM(A1:A2)", "Alice"],
            "score": [80, 75, 60, 90, 85],
        }
    )
    safe = sanitize_dataframe_for_export(df)
    assert safe.loc[0, "name"].startswith("'=")
    assert safe.loc[1, "name"].startswith("'+")
    assert safe.loc[2, "name"].startswith("'-")
    assert safe.loc[3, "name"].startswith("'@")
    assert safe.loc[4, "name"] == "Alice"


def test_validate_uploaded_csv_accepts_valid_csv_and_rejects_bad_inputs(tmp_path):
    valid_path = tmp_path / "students.csv"
    df = generate_demo_data(number_of_students=15, random_seed=42)
    df.to_csv(valid_path, index=False)

    parsed, warnings_list = validate_uploaded_csv(valid_path, "students.csv", "text/csv")
    assert len(parsed) == 15
    assert isinstance(warnings_list, list)

    bad_ext = tmp_path / "malware.exe"
    bad_ext.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported file extension"):
        validate_uploaded_csv(bad_ext, "malware.exe", "application/octet-stream")

    dup_cols = tmp_path / "dup_cols.csv"
    dup_cols.write_text("age,age\n20,21\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate column names"):
        validate_uploaded_csv(dup_cols, "dup_cols.csv", "text/csv")


def test_profile_dataframe_and_build_sdv_metadata():
    df = generate_demo_data(number_of_students=25, random_seed=42)
    profile = profile_dataframe(df)

    assert profile["row_count"] == 25
    assert profile["column_count"] == 11
    assert "student_id" in profile["identifier_candidates"]
    assert "grade" in profile["sensitive_candidates"]
    assert "age" in profile["numerical_columns"]
    assert len(profile["correlation_matrix"]) >= 2

    metadata = build_sdv_metadata(
        df.drop(columns=["student_id"]),
        table_name="student_records",
        column_overrides={"year_of_study": "ordinal"},
    )
    meta_dict = metadata.to_dict()
    assert meta_dict["tables"]["student_records"]["columns"]["year_of_study"]["sdtype"] == "ordinal"
