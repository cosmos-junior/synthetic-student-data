"""Workflows for dataset upload/profiling, synthetic generation, evaluation, and PDF reports."""

import io
import math
import time
import uuid
from pathlib import Path

import pandas as pd
import sdv
from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sdv.single_table import (
    CTGANSynthesizer,
    GaussianCopulaSynthesizer,
    TVAESynthesizer,
)
from sklearn.model_selection import train_test_split

from src.synthetic_data.evaluate_models import (
    evaluate_all_models,
    evaluate_ml_utility,
    evaluate_privacy_risk,
    evaluate_statistical_fidelity,
)
from src.synthetic_data.generation_utils import (
    apply_student_post_processing,
    run_synthesizer_pipeline,
    set_reproducible_seed,
)
from src.synthetic_data.profiling import (
    build_sdv_metadata,
    compute_file_sha256,
    profile_dataframe,
    validate_uploaded_csv,
)
from src.synthetic_data.validation import validate_student_data

from .models import AuditLog, EvaluationResult, GenerationJob, InstitutionalDataset


def log_audit_event(user, action: str, resource_type: str, resource_id: str = "", details: dict | None = None):
    AuditLog.objects.create(
        user=user if (user and user.is_authenticated) else None,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        details=details or {},
    )


def ingest_uploaded_dataset(
    user,
    uploaded_file,
    name: str,
    description: str,
    category: str,
    authorization_confirmed: bool,
) -> InstitutionalDataset:
    """Validate, store privately, profile, and build SDV metadata for an uploaded CSV."""

    if not authorization_confirmed:
        raise ValueError("Authorization confirmation is required before processing institutional data.")

    dataset_id = uuid.uuid4()
    safe_dir = settings.PROJECT_ROOT / "data" / "uploads" / str(user.id)
    safe_dir.mkdir(parents=True, exist_ok=True)
    dest_path = safe_dir / f"{dataset_id}.csv"

    with open(dest_path, "wb+") as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)

    try:
        df, warnings_list = validate_uploaded_csv(
            dest_path,
            original_filename=uploaded_file.name,
            content_type=getattr(uploaded_file, "content_type", ""),
        )
    except Exception:
        if dest_path.exists():
            dest_path.unlink()
        raise

    profile = profile_dataframe(df)
    overrides = {
        col_info["name"]: col_info["detected_sdtype"]
        for col_info in profile["columns"]
    }
    model_df = df.drop(columns=profile["identifier_candidates"], errors="ignore")
    metadata = build_sdv_metadata(
        model_df,
        table_name="records",
        column_overrides={k: v for k, v in overrides.items() if k in model_df.columns and v != "id"},
    )

    dataset = InstitutionalDataset.objects.create(
        id=dataset_id,
        name=name or Path(uploaded_file.name).stem,
        description=description,
        category=category,
        original_filename=Path(uploaded_file.name).name,
        file_path=f"data/uploads/{user.id}/{dataset_id}.csv",
        file_size_bytes=dest_path.stat().st_size,
        file_sha256=compute_file_sha256(dest_path),
        row_count=profile["row_count"],
        column_count=profile["column_count"],
        authorization_confirmed=True,
        profile_json=profile,
        metadata_json=metadata.to_dict(),
        column_overrides=overrides,
        metadata_confirmed=False,
        validation_warnings=warnings_list,
        owner=user,
    )
    log_audit_event(
        user,
        "upload_dataset",
        "InstitutionalDataset",
        str(dataset.id),
        {"filename": dataset.original_filename, "rows": dataset.row_count},
    )
    return dataset


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
    """Run a synthetic data generation experiment, validate, evaluate, and persist metrics."""

    if job.status == GenerationJob.Status.CANCELLED:
        return job

    started = time.perf_counter()
    job.status = GenerationJob.Status.RUNNING
    job.started_at = timezone.now()
    job.sdv_version = sdv.__version__
    job.save(update_fields=["status", "started_at", "sdv_version"])

    jobs_dir = settings.PROJECT_ROOT / "outputs" / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    relative_output = f"outputs/jobs/{job.id}_{job.model_type}.csv"

    try:
        if job.dataset is not None:
            source_path = settings.PROJECT_ROOT / job.dataset.file_path
            training_df = pd.read_csv(source_path)
            is_student_case = job.dataset.category == InstitutionalDataset.Category.STUDENT_ACADEMIC
            id_cols = [
                col for col, sdtype in job.dataset.column_overrides.items()
                if sdtype == "id"
            ] or job.dataset.profile_json.get("identifier_candidates", [])
            table_name = "records"
            job.dataset_fingerprint = job.dataset.file_sha256
            model_df = training_df.drop(columns=id_cols, errors="ignore")
            overrides = {
                k: v for k, v in job.dataset.column_overrides.items()
                if k in model_df.columns and v != "id"
            }
            metadata = build_sdv_metadata(model_df, table_name=table_name, column_overrides=overrides)
        else:
            default_path = settings.PROJECT_ROOT / "data" / "processed" / "student_training_data.csv"
            training_df = pd.read_csv(default_path)
            is_student_case = True
            id_cols = ["student_id"]
            table_name = "student_records"
            job.dataset_fingerprint = compute_file_sha256(default_path)
            model_df = training_df.copy()
            metadata = None

        job.training_row_count = len(training_df)

        df = run_synthesizer_pipeline(
            synthesizer_factory=_build_synthesizer_factory(job),
            model_name=job.get_model_type_display(),
            output_filename=f"jobs/{job.id}_{job.model_type}.csv",
            number_of_rows=job.num_rows,
            training_data=training_df,
            metadata=metadata,
            table_name=table_name,
            identifier_columns=id_cols,
            apply_student_rules=is_student_case,
            random_seed=job.random_seed,
        )

        if is_student_case and "student_id" in df.columns:
            errors = validate_student_data(df)
        else:
            errors = []

        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        numeric_summary = df[numeric_cols].agg(["mean", "std", "min", "max"]).round(2).to_dict() if numeric_cols else {}

        # Per-experiment fidelity & privacy evaluation
        eval_real = model_df
        eval_synth = df.drop(columns=id_cols, errors="ignore")
        eval_meta = (metadata or build_sdv_metadata(eval_real, table_name=table_name)).to_dict()

        fidelity = evaluate_statistical_fidelity(eval_real, eval_synth, eval_meta, table_name=table_name)
        privacy = evaluate_privacy_risk(eval_real, eval_synth, eval_meta, table_name=table_name)

        ml_utility = {}
        target_col = (job.model_config or {}).get("target_column") or (
            "academic_status" if is_student_case and "academic_status" in eval_real.columns else None
        )
        reg_col = (job.model_config or {}).get("regression_target") or (
            "final_score" if is_student_case and "final_score" in eval_real.columns else None
        )
        if target_col and target_col in eval_real.columns and len(eval_real) >= 30:
            set_reproducible_seed(job.random_seed)
            stratify_col = eval_real[target_col] if eval_real[target_col].value_counts().min() >= 2 else None
            r_train, r_test = train_test_split(
                eval_real, test_size=0.2, random_state=job.random_seed, stratify=stratify_col
            )
            holdout_synth = _build_synthesizer_factory(job)(
                build_sdv_metadata(r_train, table_name=table_name)
            )
            holdout_synth.fit({table_name: r_train})
            sampled = holdout_synth.sample(num_rows=len(r_train))
            split_df = sampled[table_name] if isinstance(sampled, dict) else sampled
            if is_student_case:
                split_df = apply_student_post_processing(split_df)
            ml_utility = {
                "trtr": evaluate_ml_utility(r_train, r_test, target_column=target_col, regression_target=reg_col),
                "tstr": evaluate_ml_utility(split_df, r_test, target_column=target_col, regression_target=reg_col),
            }

        job.output_file = relative_output
        job.validation_passed = len(errors) == 0
        job.validation_errors = errors
        job.summary_stats = {
            "num_records": len(df),
            "numeric": numeric_summary,
        }
        if "academic_status" in df.columns:
            job.summary_stats["academic_status_counts"] = df["academic_status"].value_counts().to_dict()
        if "programme" in df.columns:
            job.summary_stats["programme_counts"] = df["programme"].value_counts().to_dict()

        job.evaluation_json = {
            "fidelity": fidelity,
            "privacy": privacy,
            "ml_utility": ml_utility,
        }
        job.status = GenerationJob.Status.COMPLETED
        job.completed_at = timezone.now()
        job.duration_seconds = round(time.perf_counter() - started, 2)
    except Exception as exc:
        job.status = GenerationJob.Status.FAILED
        job.error_message = str(exc)
        job.completed_at = timezone.now()
        job.duration_seconds = round(time.perf_counter() - started, 2)

    job.save()
    return job


def _clean_float(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return float(value)


def run_comparative_evaluation() -> list[EvaluationResult]:
    """Run leak-free comparative evaluation across all models and persist results."""

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
                "dcr_mean": _clean_float(record.get("dcr_mean")),
                "dcr_min": _clean_float(record.get("dcr_min")),
                "dcr_p05": _clean_float(record.get("dcr_p05")),
                "exact_duplicate_rate": _clean_float(record.get("exact_duplicate_rate")),
                "near_duplicate_rate": _clean_float(record.get("near_duplicate_rate")),
                "membership_inference_risk": _clean_float(record.get("membership_inference_risk")),
                "privacy_risk_label": record.get("privacy_risk_label", ""),
                "status_accuracy": _clean_float(record["status_accuracy"]),
                "status_macro_f1": _clean_float(record["status_macro_f1"]),
                "final_score_r2": _clean_float(record["final_score_r2"]),
                "final_score_rmse": _clean_float(record["final_score_rmse"]),
            },
        )
        results.append(obj)
    return results


def build_experiment_pdf_report(job: GenerationJob) -> bytes:
    """Generate a downloadable PDF evaluation report for a completed GenerationJob."""

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("Synthetic Tabular Data Experiment Report", styles["Title"]),
        Spacer(1, 10),
        Paragraph(f"<b>Experiment ID:</b> {job.id}", styles["Normal"]),
        Paragraph(f"<b>Model:</b> {job.get_model_type_display()} (SDV {job.sdv_version or 'N/A'})", styles["Normal"]),
        Paragraph(f"<b>Rows Generated:</b> {job.num_rows} | <b>Random Seed:</b> {job.random_seed} | <b>Duration:</b> {job.duration_seconds or 0:.2f}s", styles["Normal"]),
        Paragraph(f"<b>Validation Passed:</b> {job.validation_passed}", styles["Normal"]),
        Spacer(1, 14),
    ]

    eval_data = job.evaluation_json or {}
    for section_title, key in [
        ("Statistical Fidelity Metrics", "fidelity"),
        ("Privacy Risk Indicators (Empirical, Not Formal DP)", "privacy"),
    ]:
        section_dict = eval_data.get(key, {})
        if section_dict:
            elements.append(Paragraph(section_title, styles["Heading2"]))
            rows = [["Metric", "Value"]] + [[str(k), str(v)] for k, v in section_dict.items()]
            table = Table(rows, colWidths=[260, 180])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ]
                )
            )
            elements.append(table)
            elements.append(Spacer(1, 12))

    elements.append(
        Paragraph(
            "<b>Limitations:</b> Privacy indicators (DCR, NewRowSynthesis, DisclosureProtection) are empirical "
            "measurements and do not constitute formal differential privacy guarantees.",
            styles["Italic"],
        )
    )
    doc.build(elements)
    return buffer.getvalue()
