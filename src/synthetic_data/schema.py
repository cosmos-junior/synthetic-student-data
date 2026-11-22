
"""
Central schema for the synthetic student data project.
"""

ID_COLUMN = "student_id"

NUMERIC_COLUMNS = [
    "age",
    "year_of_study",
    "attendance_percentage",
    "coursework_score",
    "exam_score",
    "final_score",
]

CATEGORICAL_COLUMNS = [
    "gender",
    "programme",
    "grade",
    "academic_status",
]

REQUIRED_COLUMNS = [
    ID_COLUMN,
    *NUMERIC_COLUMNS,
    *CATEGORICAL_COLUMNS,
]

PROGRAMMES = ["BIT", "BCS", "BBIT", "BSE"]

GENDERS = ["Male", "Female"]

GRADES = ["A", "B", "C", "D", "E"]

ACADEMIC_STATUSES = ["Pass", "Fail"]

COLUMN_RANGES = {
    "age": (17, 35),
    "year_of_study": (1, 4),
    "attendance_percentage": (0, 100),
    "coursework_score": (0, 100),
    "exam_score": (0, 100),
    "final_score": (0, 100),
}

PASS_MARK = 40

COURSEWORK_WEIGHT = 0.40
EXAM_WEIGHT = 0.60


def determine_grade(score):
    """Determine the illustrative academic grade."""

    if score >= 70:
        return "A"
    elif score >= 60:
        return "B"
    elif score >= 50:
        return "C"
    elif score >= 40:
        return "D"
    else:
        return "E"


def determine_status(score):
    """Determine academic pass or fail status."""

    return "Pass" if score >= PASS_MARK else "Fail"
