
from src.synthetic_data.generate_demo_data import generate_demo_data
from src.synthetic_data.validation import validate_student_data


def test_demo_dataset_generation():
    data = generate_demo_data(500)

    assert len(data) == 500
    assert data["student_id"].is_unique
    assert validate_student_data(data) == []


def test_demo_data_reproducibility():
    first = generate_demo_data(100, random_seed=42)
    second = generate_demo_data(100, random_seed=42)

    assert first.equals(second)


def test_final_score_calculation():
    data = generate_demo_data(100)

    expected = (
        data["coursework_score"] * 0.40
        + data["exam_score"] * 0.60
    ).round(2)

    assert data["final_score"].equals(expected)





