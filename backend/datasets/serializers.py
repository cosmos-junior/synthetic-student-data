"""DRF serializers for auth, institutional datasets, experiments, and evaluations."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import AuditLog, EvaluationResult, GenerationJob, InstitutionalDataset

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """Registers a new researcher user account."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "is_staff", "date_joined"]
        read_only_fields = fields


class InstitutionalDatasetSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = InstitutionalDataset
        fields = [
            "id",
            "name",
            "description",
            "category",
            "category_display",
            "original_filename",
            "file_size_bytes",
            "file_sha256",
            "row_count",
            "column_count",
            "authorization_confirmed",
            "profile_json",
            "metadata_json",
            "column_overrides",
            "metadata_confirmed",
            "validation_warnings",
            "owner_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class MetadataConfirmSerializer(serializers.Serializer):
    column_overrides = serializers.DictField(child=serializers.CharField())


class GenerationJobCreateSerializer(serializers.ModelSerializer):
    """Validates parameters for launching a synthetic data generation experiment."""

    dataset = serializers.PrimaryKeyRelatedField(
        queryset=InstitutionalDataset.objects.all(),
        required=False,
        allow_null=True,
    )
    random_seed = serializers.IntegerField(required=False, default=42)
    model_config = serializers.JSONField(required=False, default=dict)

    class Meta:
        model = GenerationJob
        fields = [
            "dataset",
            "model_type",
            "num_rows",
            "epochs",
            "batch_size",
            "random_seed",
            "model_config",
        ]

    def validate_num_rows(self, value: int) -> int:
        if not 10 <= value <= 10000:
            raise serializers.ValidationError("num_rows must be between 10 and 10000.")
        return value

    def validate_epochs(self, value: int) -> int:
        if not 1 <= value <= 2000:
            raise serializers.ValidationError("epochs must be between 1 and 2000.")
        return value

    def validate(self, attrs: dict) -> dict:
        request = self.context.get("request")
        dataset = attrs.get("dataset")
        if dataset and request and not request.user.is_staff and dataset.owner != request.user:
            raise serializers.ValidationError({"dataset": "You do not have access to this dataset."})

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
    """Full representation of a generation experiment."""

    model_type_display = serializers.CharField(source="get_model_type_display", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    dataset_name = serializers.CharField(source="dataset.name", read_only=True, default="Built-in Student Training Data")

    class Meta:
        model = GenerationJob
        fields = [
            "id",
            "dataset",
            "dataset_name",
            "dataset_fingerprint",
            "model_type",
            "model_type_display",
            "num_rows",
            "epochs",
            "batch_size",
            "random_seed",
            "training_row_count",
            "sdv_version",
            "model_config",
            "status",
            "output_file",
            "validation_passed",
            "validation_errors",
            "summary_stats",
            "evaluation_json",
            "error_message",
            "duration_seconds",
            "created_by_username",
            "created_at",
            "started_at",
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
            "dcr_mean",
            "dcr_min",
            "dcr_p05",
            "exact_duplicate_rate",
            "near_duplicate_rate",
            "membership_inference_risk",
            "privacy_risk_label",
            "status_accuracy",
            "status_macro_f1",
            "final_score_r2",
            "final_score_rmse",
            "evaluated_at",
        ]


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = AuditLog
        fields = ["id", "username", "action", "resource_type", "resource_id", "details", "created_at"]
