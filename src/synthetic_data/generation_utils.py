"""Shared pipeline helpers for synthetic student data generation."""

from pathlib import Path
import pandas as pd

from src.synthetic_data.configure_metadata import configure_metadata
from src.synthetic_data.schema import (
    COURSEWORK_WEIGHT,
    EXAM_WEIGHT,
    determine_grade,
    determine_status,
)
from src.synthetic_data.validation import validate_student_data


def run_synthesizer_pipeline(
    synthesizer_factory,
    model_name: str,
    output_filename: str,
    number_of_rows: int = 500,
) -> pd.DataFrame:
    """Train an SDV synthesizer, sample rows, post-process, save, and validate."""

    project_root = Path(__file__).resolve().parents[2]
    input_file = (
        project_root
        / "data"
        / "processed"
        / "student_training_data.csv"
    )
    output_directory = project_root / "outputs"
    output_directory.mkdir(parents=True, exist_ok=True)

    training_data = pd.read_csv(input_file)
    metadata = configure_metadata()
    synthesizer = synthesizer_factory(metadata)

    print(f"\nTraining {model_name} model...")
    synthesizer.fit({"student_records": training_data})
    print("Model training completed.")

    print("\nGenerating synthetic student records...")
    sampled_data = synthesizer.sample(num_rows=number_of_rows)
    synthetic_data = (
        sampled_data["student_records"]
        if isinstance(sampled_data, dict)
        else sampled_data
    )

    # Recompute derived academic columns deterministically.
    synthetic_data["final_score"] = (
        synthetic_data["coursework_score"] * COURSEWORK_WEIGHT
        + synthetic_data["exam_score"] * EXAM_WEIGHT
    ).round(2)
    synthetic_data["grade"] = synthetic_data["final_score"].apply(determine_grade)
    synthetic_data["academic_status"] = synthetic_data["final_score"].apply(determine_status)

    # Add new synthetic identifiers.
    synthetic_data.insert(
        0,
        "student_id",
        [f"IN17{i:05d}" for i in range(1, number_of_rows + 1)],
    )

    output_file = output_directory / output_filename
    synthetic_data.to_csv(output_file, index=False)

    print("\nSynthetic data generated.")
    print("Records:", len(synthetic_data))
    print("Columns:", len(synthetic_data.columns))
    print("Saved to:", output_file)

    errors = validate_student_data(synthetic_data)

    print("\n========== VALIDATION RESULTS ==========")
    if errors:
        print("Validation found issues:")
        for error in errors:
            print("-", error)
    else:
        print("All validation checks passed.")

    print("\nFirst five synthetic records:")
    print(synthetic_data.head())

    print("\nNumerical summary:")
    print(synthetic_data.describe().round(2))

    return synthetic_data
