"""Database models for institutional datasets, generation experiments, evaluations, and audit logs."""

import uuid
from django.conf import settings
from django.db import models


class InstitutionalDataset(models.Model):
    """Stores metadata and profiling results for an uploaded authorized dataset."""

    class Category(models.TextChoices):
        STUDENT_ACADEMIC = "student_academic", "Student Academic"
        INSTITUTIONAL_GENERIC = "institutional_generic", "Institutional Generic"
        RESEARCH_BENCHMARK = "research_benchmark", "Research Benchmark"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=32,
        choices=Category.choices,
        default=Category.STUDENT_ACADEMIC,
    )
    original_filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    file_sha256 = models.CharField(max_length=64, blank=True)
    row_count = models.PositiveIntegerField(default=0)
    column_count = models.PositiveIntegerField(default=0)
    authorization_confirmed = models.BooleanField(default=False)
    profile_json = models.JSONField(default=dict, blank=True)
    metadata_json = models.JSONField(default=dict, blank=True)
    column_overrides = models.JSONField(default=dict, blank=True)
    metadata_confirmed = models.BooleanField(default=False)
    validation_warnings = models.JSONField(default=list, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="institutional_datasets",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.row_count}x{self.column_count})"


class GenerationJob(models.Model):
    """Tracks a synthetic dataset generation experiment and its evaluation metrics."""

    class ModelType(models.TextChoices):
        GAUSSIAN_COPULA = "gaussian_copula", "Gaussian Copula"
        CTGAN = "ctgan", "CTGAN"
        TVAE = "tvae", "TVAE"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dataset = models.ForeignKey(
        InstitutionalDataset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="experiments",
    )
    dataset_fingerprint = models.CharField(max_length=64, blank=True)
    model_type = models.CharField(max_length=32, choices=ModelType.choices)
    num_rows = models.PositiveIntegerField(default=500)
    epochs = models.PositiveIntegerField(default=300)
    batch_size = models.PositiveIntegerField(default=500)
    random_seed = models.IntegerField(default=42)
    training_row_count = models.PositiveIntegerField(default=0)
    sdv_version = models.CharField(max_length=32, blank=True)
    model_config = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    output_file = models.CharField(max_length=255, blank=True)
    validation_passed = models.BooleanField(default=False)
    validation_errors = models.JSONField(default=list, blank=True)
    summary_stats = models.JSONField(default=dict, blank=True)
    evaluation_json = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generation_jobs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_model_type_display()} ({self.num_rows} rows) - {self.status}"


class EvaluationResult(models.Model):
    """Stores comparative benchmark evaluation metrics across models."""

    model_name = models.CharField(max_length=64, unique=True)
    quality_overall = models.FloatField()
    column_shapes = models.FloatField()
    column_pair_trends = models.FloatField()
    data_validity = models.FloatField()
    data_structure = models.FloatField()
    new_row_synthesis = models.FloatField(null=True, blank=True)
    dcr_baseline_protection = models.FloatField(null=True, blank=True)
    disclosure_protection = models.FloatField(null=True, blank=True)
    dcr_mean = models.FloatField(null=True, blank=True)
    dcr_min = models.FloatField(null=True, blank=True)
    dcr_p05 = models.FloatField(null=True, blank=True)
    exact_duplicate_rate = models.FloatField(null=True, blank=True)
    near_duplicate_rate = models.FloatField(null=True, blank=True)
    membership_inference_risk = models.FloatField(null=True, blank=True)
    privacy_risk_label = models.CharField(max_length=64, blank=True)
    status_accuracy = models.FloatField()
    status_macro_f1 = models.FloatField()
    final_score_r2 = models.FloatField()
    final_score_rmse = models.FloatField()
    evaluated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.model_name} (Quality={self.quality_overall:.4f})"


class AuditLog(models.Model):
    """Audit trail for dataset uploads, experiments, downloads, and deletions."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=64)
    resource_type = models.CharField(max_length=64)
    resource_id = models.CharField(max_length=64, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} ({self.resource_type}:{self.resource_id})"
