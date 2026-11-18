"""
Validation functions for student academic datasets.
"""
import pandas as pd

from .schema import(
    NUMERIC_COLUMNS,
    CATEGORICAL_COLUMNS,
    COLUMN_RANGES,
    PROGRAMMES,
    GENDERS,
    GRADES,
    ACADEMIC_STATUSES,
    PASS_MARK,
    COURSEWORK_WEIGHT,
    EXAM_WEIGHT,
)

REQUIRED_COLUMNS= [
    "student_reg",
    "NUMERIC_COLUMNS",
    "CATEGORICAL_COLUMNS",
]

def validate_student_data(data: pd.DataFrame) -> list:
     """
    Validate a student academic dataset.

    Returns a list of validation errors.
    An empty list means all checks passed.
    """
     errors= []
    #check required columns
     missing = set(REQUIRED_COLUMNS) - set(data.columns)
     if missing:
        errors.append(f"Missing columns: {sorted(missing)}")
        return errors
    #check unique REGS
     if data["student_reg"].duplicate().any():
        errors.append("Student Reg number must be unique.")

    #check numerical ranges
     for column, (minimum, maximum) in COLUMN_RANGES.items():
        if not pd.api.types.is_numeric_dtype(data[column]):
            errors.append(f"{column} must be numeric.")
            continue
        if data[column].isna().any():
            errors.append(f"{column} contains missing values")
            continue
        if not data[column].between(minimum, maximum).all():
            errors.append(f"{column} must be between {minimum} and {maximum}.")
     # Check categorical values
     allowed_categories = {
        "gender": GENDERS,
        "programme": PROGRAMMES,
        "grade": GRADES,
        "academic_status": ACADEMIC_STATUSES,
    }

     for column, allowed in allowed_categories.items():

        if not data[column].isin(allowed).all():
            errors.append(
                f"{column} contains invalid categories."
            )

     # Check final score relationship
     expected_final = (
        data["coursework_score"] * COURSEWORK_WEIGHT
        + data["exam_score"] * EXAM_WEIGHT
    )

     if not (
        (data["final_score"] - expected_final).abs() <= 0.1
    ).all():
        errors.append("Final scores do not follow the weighted formula.")

    # Check academic status
     expected_status = data["final_score"].apply(
        lambda score: "Pass" if score >= PASS_MARK else "Fail"
    )

     if not data["academic_status"].equals(expected_status):
        errors.append("Academic status does not match final scores.")

     return errors
