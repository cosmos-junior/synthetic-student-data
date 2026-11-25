"""DRF serializers for generation jobs and evaluation results."""

from rest_framework import serializers

from .models import EvaluationResult, GenerationJob


class GenerationJobCreateSerializer(serializers.ModelSerializer):
    """Validates parameters for launching a synthetic data generation job."""

    class Meta:
        model = GenerationJob
        fields = ["model_type", "num_rows", "epochs", "batch_size"]

    def validate_num_rows(self, value: int) -> int:
        if not 10 <= value <= 10000:
            raise serializers.ValidationError("num_rows must be between 10 and 10000.")
        return value

    def validate_epochs(self, value: int) -> int:
        if not 1 <= value <= 2000:
            raise serializers.ValidationError("epochs must be between 1 and 2000.")
        return value

    def validate(self, attrs: dict) -> dict:
        model_type = attrs.get("model_type")
        batch_size = attrs.get("batch_size", 500)
        if batch_size < 10:
            raise serializers.ValidationError({"batch_size": "batch_size must be at least 10."})
        if model_type == GenerationJob.ModelType.CTGAN and batch_size % 10 != 0:
            raise serializers.ValidationError(
                {"batch_size": "CTGAN requires batch_size to be divisible by pac (10)."}
            )
        return attrs


class GenerationJobSerializer(serializers.ModelSerializer):
    """Full representation of a generation job."""

    model_type_display = serializers.CharField(source="get_model_type_display", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = GenerationJob
        fields = [
            "id",
            "model_type",
            "model_type_display",
            "num_rows",
            "epochs",
            "batch_size",
            "status",
            "output_file",
            "validation_passed",
            "validation_errors",
            "summary_stats",
            "error_message",
            "created_by_username",
            "created_at",
            "completed_at",
        ]
        read_only_fields = fields


class EvaluationResultSerializer(serializers.ModelSerializer):
    """Serializes comparative model evaluation metrics."""

    class Meta:
        model = EvaluationResult
        fields = [
            "id",
            "model_name",
            "quality_overall",
            "column_shapes",
            "column_pair_trends",
            "data_validity",
            "data_structure",
            "new_row_synthesis",
            "dcr_baseline_protection",
            "disclosure_protection",
            "status_accuracy",
            "status_macro_f1",
            "final_score_r2",
            "final_score_rmse",
            "evaluated_at",
        ]

