"""REST API views for synthetic student data generation and evaluation."""

import pandas as pd
from django.conf import settings
from django.http import FileResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EvaluationResult, GenerationJob
from .serializers import (
    EvaluationResultSerializer,
    GenerationJobCreateSerializer,
    GenerationJobSerializer,
)
from .services import execute_generation_job, run_comparative_evaluation


class HealthCheckView(APIView):
    """Public health-check endpoint."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok", "service": "synthetic-student-data-api"})


class GenerationJobViewSet(viewsets.ModelViewSet):
    """Create, inspect, preview, and download synthetic dataset generation jobs."""

    queryset = GenerationJob.objects.all()
    http_method_names = ["get", "post", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return GenerationJobCreateSerializer
        return GenerationJobSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = serializer.save(created_by=request.user)
        execute_generation_job(job)
        output_serializer = GenerationJobSerializer(job)
        http_status = (
            status.HTTP_201_CREATED
            if job.status == GenerationJob.Status.COMPLETED
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        return Response(output_serializer.data, status=http_status)

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        job = self.get_object()
        if job.status != GenerationJob.Status.COMPLETED or not job.output_file:
            return Response(
                {"detail": "Dataset is not available for preview."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        limit = min(int(request.query_params.get("limit", 10)), 100)
        file_path = settings.PROJECT_ROOT / job.output_file
        df = pd.read_csv(file_path)
        return Response(
            {
                "job_id": str(job.id),
                "total_rows": len(df),
                "columns": list(df.columns),
                "rows": df.head(limit).to_dict(orient="records"),
            }
        )

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        job = self.get_object()
        if job.status != GenerationJob.Status.COMPLETED or not job.output_file:
            return Response(
                {"detail": "Dataset is not available for download."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        file_path = settings.PROJECT_ROOT / job.output_file
        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename=file_path.name,
            content_type="text/csv",
        )


class EvaluationResultListView(APIView):
    """List comparative evaluation metrics across all models."""

    def get(self, request):
        queryset = EvaluationResult.objects.all()
        serializer = EvaluationResultSerializer(queryset, many=True)
        return Response(serializer.data)


class RunEvaluationView(APIView):
    """Trigger comparative evaluation and persist updated results."""

    def post(self, request):
        results = run_comparative_evaluation()
        serializer = EvaluationResultSerializer(results, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

