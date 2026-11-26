"""Shared pipeline helpers for synthetic tabular data generation."""

from pathlib import Path
import random
import time
import numpy as np
import pandas as pd
import sdv

from src.synthetic_data.configure_metadata import TABLE_NAME, configure_metadata
from src.synthetic_data.profiling import build_sdv_metadata, sanitize_dataframe_for_export
from src.synthetic_data.schema import (
    COURSEWORK_WEIGHT,
    EXAM_WEIGHT,
    determine_grade,
    determine_status,
)
from src.synthetic_data.validation import validate_student_data


def set_reproducible_seed(random_seed: int | None) -> None:
    """Set Python, NumPy, and PyTorch (if installed) random seeds."""
    if random_seed is None:
        return
    random.seed(random_seed)
    np.random.seed(random_seed)
    try:
        import torch

        torch.manual_seed(random_seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(random_seed)
    except ImportError:
        pass


def apply_student_post_processing(df: pd.DataFrame) -> pd.DataFrame:
    """Apply deterministic academic rules for the student academic dataset."""
    required = {"coursework_score", "exam_score"}
    if not required.issubset(df.columns):
        return df
    out = df.copy()
    out["final_score"] = (
        out["coursework_score"] * COURSEWORK_WEIGHT
        + out["exam_score"] * EXAM_WEIGHT
    ).round(2)
    out["grade"] = out["final_score"].apply(determine_grade)
    out["academic_status"] = out["final_score"].apply(determine_status)
    return out


def run_synthesizer_pipeline(
    synthesizer_factory,
    model_name: str,
    output_filename: str,
    number_of_rows: int = 500,
    training_data: pd.DataFrame | None = None,
    metadata=None,
    table_name: str = TABLE_NAME,
    identifier_columns: list[str] | None = None,
    apply_student_rules: bool = True,
    random_seed: int | None = 42,
    save_output: bool = True,
) -> pd.DataFrame:
    """Train an SDV synthesizer, sample rows, post-process, save, and validate."""

    set_reproducible_seed(random_seed)
    project_root = Path(__file__).resolve().parents[2]
    output_directory = project_root / "outputs"
    output_directory.mkdir(parents=True, exist_ok=True)

    if training_data is None:
        input_file = project_root / "data" / "processed" / "student_training_data.csv"
        training_data = pd.read_csv(input_file)

    id_cols = identifier_columns or ["student_id"]
    cols_to_drop = [c for c in id_cols if c in training_data.columns]
    model_training_df = training_data.drop(columns=cols_to_drop) if cols_to_drop else training_data.copy()

    if metadata is None:
        if table_name == TABLE_NAME and set(model_training_df.columns) >= {
            "age",
            "gender",
            "programme",
            "year_of_study",
            "coursework_score",
            "exam_score",
            "final_score",
        }:
            metadata = configure_metadata()
        else:
            metadata = build_sdv_metadata(model_training_df, table_name=table_name)

    synthesizer = synthesizer_factory(metadata)

    start_time = time.perf_counter()
    print(f"\nTraining {model_name} model (sdv {sdv.__version__})...")
    synthesizer.fit({table_name: model_training_df})
    print("Model training completed.")

    print("\nGenerating synthetic records...")
    sampled_data = synthesizer.sample(num_rows=number_of_rows)
    synthetic_data = (
        sampled_data[table_name]
        if isinstance(sampled_data, dict)
        else sampled_data
    )

    if apply_student_rules:
        synthetic_data = apply_student_post_processing(synthetic_data)

    # Generate fresh synthetic identifiers (preserving agreed IN1700001 format for student_id)
    for col in id_cols:
        if col == "student_id" or col not in synthetic_data.columns:
            prefix = "IN17" if col == "student_id" else "SYN"
            synthetic_data.insert(
                0 if col == "student_id" else len(synthetic_data.columns),
                col,
                [f"{prefix}{i:05d}" for i in range(1, number_of_rows + 1)],
            )

    if save_output:
        output_file = output_directory / output_filename
        output_file.parent.mkdir(parents=True, exist_ok=True)
        safe_df = sanitize_dataframe_for_export(synthetic_data)
        safe_df.to_csv(output_file, index=False)
        print(f"Saved to: {output_file} (elapsed {time.perf_counter() - start_time:.2f}s)")

    if apply_student_rules and "student_id" in synthetic_data.columns:
        errors = validate_student_data(synthetic_data)
        print("\n========== VALIDATION RESULTS ==========")
        if errors:
            print("Validation found issues:")
            for error in errors:
                print("-", error)
        else:
            print("All validation checks passed.")

    return synthetic_data
