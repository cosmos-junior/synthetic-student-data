"""Database models for synthetic dataset generation jobs and evaluations."""

import uuid
from django.conf import settings
from django.db import models


class GenerationJob(models.Model):
    """Tracks a synthetic student dataset generation run."""

    class ModelType(models.TextChoices):
        GAUSSIAN_COPULA = "gaussian_copula", "Gaussian Copula"
        CTGAN = "ctgan", "CTGAN"
        TVAE = "tvae", "TVAE"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_type = models.CharField(max_length=32, choices=ModelType.choices)
    num_rows = models.PositiveIntegerField(default=500)
    epochs = models.PositiveIntegerField(default=300)
    batch_size = models.PositiveIntegerField(default=500)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    output_file = models.CharField(max_length=255, blank=True)
    validation_passed = models.BooleanField(default=False)
    validation_errors = models.JSONField(default=list, blank=True)
    summary_stats = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generation_jobs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_model_type_display()} ({self.num_rows} rows) - {self.status}"


class EvaluationResult(models.Model):
    """Stores comparative evaluation metrics across fidelity, privacy, and ML utility."""

    model_name = models.CharField(max_length=64, unique=True)
    quality_overall = models.FloatField()
    column_shapes = models.FloatField()
    column_pair_trends = models.FloatField()
    data_validity = models.FloatField()
    data_structure = models.FloatField()
    new_row_synthesis = models.FloatField(null=True, blank=True)
    dcr_baseline_protection = models.FloatField(null=True, blank=True)
    disclosure_protection = models.FloatField(null=True, blank=True)
    status_accuracy = models.FloatField()
    status_macro_f1 = models.FloatField()
    final_score_r2 = models.FloatField()
    final_score_rmse = models.FloatField()
    evaluated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.model_name} (Quality={self.quality_overall:.4f})"

