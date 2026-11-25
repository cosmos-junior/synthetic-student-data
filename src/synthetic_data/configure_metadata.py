
"""Configure and inspect SDV metadata for student academic data."""

from pathlib import Path
import pandas as pd

from sdv.metadata import Metadata


TABLE_NAME = "student_records"

CATEGORICAL_COLUMNS = [
    "gender",
    "programme",
    "grade",
    "academic_status",
]

NUMERICAL_COLUMNS = [
    "age",
    "attendance_percentage",
    "coursework_score",
    "exam_score",
    "final_score",
]

ORDINAL_COLUMNS = {
    "year_of_study": [1, 2, 3, 4],
}


def configure_metadata():

    project_root = Path(__file__).resolve().parents[2]

    data_file = (
        project_root
        / "data"
        / "processed"
        / "student_training_data.csv"
    )

    data = pd.read_csv(data_file)

    # Detect metadata for our single student records table.
    metadata = Metadata.detect_from_dataframes(
        {TABLE_NAME: data},
        infer_sdtypes=True,
        infer_keys=None,
        verbose=True,
    )

    # Explicitly configure the expected column types.
    for column in CATEGORICAL_COLUMNS:
        metadata.update_column(
            column,
            table_name=TABLE_NAME,
            sdtype="categorical",
        )

    for column, categories in ORDINAL_COLUMNS.items():
        metadata.update_column(
            "year_of_study",
            table_name=TABLE_NAME,
            sdtype="ordinal",
        )

    # Validate the metadata configuration.
    metadata.validate()

    print("\n========== CONFIGURED METADATA ==========")
    print(metadata.to_dict())

    print("\nMetadata validation successful.")

    return metadata


if __name__ == "__main__":
    configure_metadata()
