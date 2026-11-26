"""Django admin registration for datasets models."""

from django.contrib import admin

from .models import AuditLog, EvaluationResult, GenerationJob, InstitutionalDataset


@admin.register(InstitutionalDataset)
class InstitutionalDatasetAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "row_count", "column_count", "metadata_confirmed", "owner", "created_at")
    list_filter = ("category", "metadata_confirmed")


@admin.register(GenerationJob)
class GenerationJobAdmin(admin.ModelAdmin):
    list_display = ("id", "model_type", "num_rows", "status", "validation_passed", "created_by", "created_at")
    list_filter = ("model_type", "status", "validation_passed")
    readonly_fields = ("id", "created_at", "started_at", "completed_at")


@admin.register(EvaluationResult)
class EvaluationResultAdmin(admin.ModelAdmin):
    list_display = (
        "model_name",
        "quality_overall",
        "dcr_baseline_protection",
        "disclosure_protection",
        "privacy_risk_label",
        "status_macro_f1",
        "final_score_r2",
        "evaluated_at",
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "resource_type", "resource_id", "user", "created_at")
    list_filter = ("action", "resource_type")
