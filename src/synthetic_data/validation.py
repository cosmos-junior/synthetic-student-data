
"""
Validation functions for student academic datasets.
"""

import pandas as pd

from .schema import (
    REQUIRED_COLUMNS,
    NUMERIC_COLUMNS,
    CATEGORICAL_COLUMNS,
    COLUMN_RANGES,
    PROGRAMMES,
    GENDERS,
    GRADES,
    ACADEMIC_STATUSES,
    COURSEWORK_WEIGHT,
    EXAM_WEIGHT,
    determine_grade,
    determine_status,
)


def validate_student_data(data: pd.DataFrame) -> list:
    """Return a list of validation errors. Empty means valid."""

    errors = []

    missing_columns = set(REQUIRED_COLUMNS) - set(data.columns)

    if missing_columns:
        errors.append(
            f"Missing columns: {sorted(missing_columns)}"
        )
        return errors

    if data.empty:
        errors.append("Dataset is empty.")
        return errors

    if data[REQUIRED_COLUMNS].isna().any().any():
        errors.append("Dataset contains missing values.")

    if data["student_id"].duplicated().any():
        errors.append("Student IDs must be unique.")

    for column in NUMERIC_COLUMNS:
        if not pd.api.types.is_numeric_dtype(data[column]):
            errors.append(f"{column} must be numeric.")
            continue

        minimum, maximum = COLUMN_RANGES[column]

        if not data[column].between(minimum, maximum).all():
            errors.append(
                f"{column} must be between {minimum} and {maximum}."
            )

    for column in ["age", "year_of_study"]:
        if pd.api.types.is_numeric_dtype(data[column]):
            if not (data[column] % 1 == 0).all():
                errors.append(f"{column} must contain whole numbers.")

    allowed_categories = {
        "gender": GENDERS,
        "programme": PROGRAMMES,
        "grade": GRADES,
        "academic_status": ACADEMIC_STATUSES,
    }

    for column, allowed_values in allowed_categories.items():
        if not data[column].isin(allowed_values).all():
            errors.append(
                f"{column} contains invalid categories."
            )

    expected_final = (
        data["coursework_score"] * COURSEWORK_WEIGHT
        + data["exam_score"] * EXAM_WEIGHT
    ).round(2)

    actual_final = data["final_score"].round(2)

    if not (actual_final == expected_final).all():
        errors.append(
            "Final scores do not follow the weighted formula."
        )

    expected_grades = data["final_score"].apply(determine_grade)

    if not data["grade"].equals(expected_grades):
        errors.append("Grades do not match final scores.")

    expected_status = data["final_score"].apply(determine_status)

    if not data["academic_status"].equals(expected_status):
        errors.append(
            "Academic status does not match final scores."
        )

    return errors
