
"""
Generate demonstration student academic data.

This is simulated development data, not real institutional data.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from .schema import (
    COURSEWORK_WEIGHT,
    EXAM_WEIGHT,
    determine_grade,
    determine_status,
)


def generate_demo_data(number_of_students=500, random_seed=42):
    """Generate a reproducible demonstration dataset."""

    if number_of_students < 1:
        raise ValueError("Number of students must be at least 1.")

    rng = np.random.default_rng(random_seed)

    # Student characteristics
    gender = rng.choice(
        ["Male", "Female"],
        size=number_of_students,
        p=[0.52, 0.48],
    )

    programme = rng.choice(
        ["BIT", "BCS", "BBIT", "BSE"],
        size=number_of_students,
        p=[0.35, 0.25, 0.20, 0.20],
    )

    year = rng.choice(
        [1, 2, 3, 4],
        size=number_of_students,
        p=[0.30, 0.27, 0.24, 0.19],
    )

    age = np.clip(
        rng.normal(19 + year * 1.1, 2.2, number_of_students),
        17,
        35,
    ).round().astype(int)

    # Latent academic ability introduces shared variation
    ability = rng.normal(0, 1, number_of_students)

    # Attendance has a modest relationship with ability
    attendance = np.clip(
        76 + (ability * 5) + rng.normal(0, 11, number_of_students),
        0,
        100,
    ).round(2)

    # Academic scores share some underlying variation
    coursework = np.clip(
        57 + (ability * 11) + rng.normal(0, 10, number_of_students),
        0,
        100,
    ).round(2)

    exam = np.clip(
        54 + (ability * 12) + rng.normal(0, 12, number_of_students),
        0,
        100,
    ).round(2)

    # Final score follows the project-defined weighting
    final_score = (
        coursework * COURSEWORK_WEIGHT
        + exam * EXAM_WEIGHT
    ).round(2)

    grade = [
        determine_grade(score) for score in final_score
    ]

    academic_status = [
        determine_status(score) for score in final_score
    ]

    data = pd.DataFrame({
        "student_id": [
            f"IN17{i:05d}"
            for i in range(1, number_of_students + 1)
        ],
        "age": age,
        "gender": gender,
        "programme": programme,
        "year_of_study": year,
        "attendance_percentage": attendance,
        "coursework_score": coursework,
        "exam_score": exam,
        "final_score": final_score,
        "grade": grade,
        "academic_status": academic_status,
    })

    return data


def save_demo_data(data):
    """Save demonstration data into the project's raw data folder."""

    project_root = Path(__file__).resolve().parents[2]

    output_directory = project_root / "data" / "raw"
    output_directory.mkdir(parents=True, exist_ok=True)

    output_file = output_directory / "demo_student_data.csv"

    data.to_csv(output_file, index=False)

    return output_file


if __name__ == "__main__":
    dataset = generate_demo_data(number_of_students=500)

    output_path = save_demo_data(dataset)

    print("Demonstration dataset generated successfully.")
    print(f"Number of records: {len(dataset)}")
    print(f"Saved to: {output_path}")
    print("\nFirst five records:")
    print(dataset.head())
