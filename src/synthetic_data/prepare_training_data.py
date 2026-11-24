"""Prepare student data for synthetic model training."""

from pathlib import Path
import pandas as pd


def prepare_training_data():

    project_root = Path(__file__).resolve().parents[2]

    input_file = (
        project_root
        / "data"
        / "raw"
        / "demo_student_data.csv"
    )

    output_directory = project_root / "data" / "processed"
    output_directory.mkdir(parents=True, exist_ok=True)

    data = pd.read_csv(input_file)

    # Remove identifiers before model training.
    training_data = data.drop(columns=["student_id"])

    output_file = output_directory / "student_training_data.csv"

    training_data.to_csv(output_file, index=False)

    print("Training data prepared successfully.")
    print("Original records:", len(data))
    print("Training records:", len(training_data))
    print("Training columns:", list(training_data.columns))
    print("Saved to:", output_file)


if __name__ == "__main__":
    prepare_training_data()