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