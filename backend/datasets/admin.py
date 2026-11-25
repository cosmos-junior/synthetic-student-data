"""Django admin registration for datasets models."""

from django.contrib import admin

from .models import EvaluationResult, GenerationJob


@admin.register(GenerationJob)
class GenerationJobAdmin(admin.ModelAdmin):
    list_display = ("id", "model_type", "num_rows", "status", "validation_passed", "created_at")
    list_filter = ("model_type", "status", "validation_passed")
    readonly_fields = ("id", "created_at", "completed_at")


@admin.register(EvaluationResult)
class EvaluationResultAdmin(admin.ModelAdmin):
    list_display = (
        "model_name",
        "quality_overall",
        "dcr_baseline_protection",
        "disclosure_protection",
        "status_macro_f1",
        "final_score_r2",
        "evaluated_at",
    )

