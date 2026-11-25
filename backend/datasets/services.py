"""Workflows connecting Django jobs to the src.synthetic_data pipeline."""

import math
from django.conf import settings
from django.utils import timezone
from sdv.single_table import (
    CTGANSynthesizer,
    GaussianCopulaSynthesizer,
    TVAESynthesizer,
)

from src.synthetic_data.evaluate_models import evaluate_all_models
from src.synthetic_data.generation_utils import run_synthesizer_pipeline
from src.synthetic_data.schema import NUMERIC_COLUMNS
from src.synthetic_data.validation import validate_student_data

from .models import EvaluationResult, GenerationJob


def _build_synthesizer_factory(job: GenerationJob):
    if job.model_type == GenerationJob.ModelType.GAUSSIAN_COPULA:
        return lambda metadata: GaussianCopulaSynthesizer(
            metadata,
            enforce_min_max_values=True,
            enforce_rounding=True,
        )
    if job.model_type == GenerationJob.ModelType.CTGAN:
        return lambda metadata: CTGANSynthesizer(
            metadata,
            enforce_min_max_values=True,
            enforce_rounding=True,
            epochs=job.epochs,
            batch_size=job.batch_size,
            verbose=False,
        )
    if job.model_type == GenerationJob.ModelType.TVAE:
        return lambda metadata: TVAESynthesizer(
            metadata,
            enforce_min_max_values=True,
            enforce_rounding=True,
            epochs=job.epochs,
            batch_size=job.batch_size,
            verbose=False,
        )
    raise ValueError(f"Unsupported model_type: {job.model_type}")


def execute_generation_job(job: GenerationJob) -> GenerationJob:
    """Run a synthetic data generation job and persist validation & summary stats."""

    job.status = GenerationJob.Status.RUNNING
    job.save(update_fields=["status"])

    jobs_dir = settings.PROJECT_ROOT / "outputs" / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    relative_output = f"outputs/jobs/{job.id}_{job.model_type}.csv"

    try:
        df = run_synthesizer_pipeline(
            synthesizer_factory=_build_synthesizer_factory(job),
            model_name=job.get_model_type_display(),
            output_filename=f"jobs/{job.id}_{job.model_type}.csv",
            number_of_rows=job.num_rows,
        )
        errors = validate_student_data(df)
        numeric_summary = (
            df[NUMERIC_COLUMNS].agg(["mean", "std", "min", "max"]).round(2).to_dict()
        )
        job.output_file = relative_output
        job.validation_passed = len(errors) == 0
        job.validation_errors = errors
        job.summary_stats = {
            "num_records": len(df),
            "numeric": numeric_summary,
            "academic_status_counts": df["academic_status"].value_counts().to_dict(),
            "programme_counts": df["programme"].value_counts().to_dict(),
        }
        job.status = GenerationJob.Status.COMPLETED
        job.completed_at = timezone.now()
    except Exception as exc:
        job.status = GenerationJob.Status.FAILED
        job.error_message = str(exc)
        job.completed_at = timezone.now()

    job.save()
    return job


def _clean_float(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return float(value)


def run_comparative_evaluation() -> list[EvaluationResult]:
    """Run comparative evaluation across all models and persist results."""

    summary_df = evaluate_all_models()
    results = []
    for record in summary_df.to_dict(orient="records"):
        obj, _ = EvaluationResult.objects.update_or_create(
            model_name=record["model"],
            defaults={
                "quality_overall": _clean_float(record["quality_overall"]),
                "column_shapes": _clean_float(record["column_shapes"]),
                "column_pair_trends": _clean_float(record["column_pair_trends"]),
                "data_validity": _clean_float(record["data_validity"]),
                "data_structure": _clean_float(record["data_structure"]),
                "new_row_synthesis": _clean_float(record.get("new_row_synthesis")),
                "dcr_baseline_protection": _clean_float(record.get("dcr_baseline_protection")),
                "disclosure_protection": _clean_float(record.get("disclosure_protection")),
                "status_accuracy": _clean_float(record["status_accuracy"]),
                "status_macro_f1": _clean_float(record["status_macro_f1"]),
                "final_score_r2": _clean_float(record["final_score_r2"]),
                "final_score_rmse": _clean_float(record["final_score_rmse"]),
            },
        )
        results.append(obj)
    return results

