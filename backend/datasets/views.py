"""REST API views with strict ownership filtering, uploads, profiling, Celery tasks, and reports."""

import pandas as pd
from django.conf import settings
from django.http import FileResponse, HttpResponse
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from src.synthetic_data.profiling import build_sdv_metadata

from .models import AuditLog, EvaluationResult, GenerationJob, InstitutionalDataset
from .serializers import (
    AuditLogSerializer,
    EvaluationResultSerializer,
    GenerationJobCreateSerializer,
    GenerationJobSerializer,
    InstitutionalDatasetSerializer,
    MetadataConfirmSerializer,
    RegisterSerializer,
    UserProfileSerializer,
)
from .services import (
    build_experiment_pdf_report,
    ingest_uploaded_dataset,
    log_audit_event,
)
from .tasks import run_comparative_evaluation_task, run_generation_experiment_task


class HealthCheckView(APIView):
    """Public health-check endpoint."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok", "service": "synthetic-student-data-api"})


class RegisterView(APIView):
    """Register a new user and issue an API token."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {"token": token.key, "user": UserProfileSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class LogoutView(APIView):
    """Invalidate the caller's DRF auth token."""

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response({"detail": "Signed out successfully."})


class ProfileView(APIView):
    """Return the authenticated user's profile."""

    def get(self, request):
        return Response(UserProfileSerializer(request.user).data)


class InstitutionalDatasetViewSet(viewsets.ModelViewSet):
    """Upload, profile, explore, confirm metadata, and delete institutional datasets."""

    serializer_class = InstitutionalDatasetSerializer
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        qs = InstitutionalDataset.objects.all()
        if not self.request.user.is_staff:
            qs = qs.filter(owner=self.request.user)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(name__icontains=search)
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        return qs

    def create(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response({"file": "A CSV file is required."}, status=status.HTTP_400_BAD_REQUEST)

        auth_raw = str(request.data.get("authorization_confirmed", "")).lower()
        auth_confirmed = auth_raw in {"true", "1", "yes", "on"}

        try:
            dataset = ingest_uploaded_dataset(
                user=request.user,
                uploaded_file=uploaded_file,
                name=request.data.get("name", ""),
                description=request.data.get("description", ""),
                category=request.data.get("category", InstitutionalDataset.Category.STUDENT_ACADEMIC),
                authorization_confirmed=auth_confirmed,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            InstitutionalDatasetSerializer(dataset).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        dataset = self.get_object()
        file_path = settings.PROJECT_ROOT / dataset.file_path
        dataset_id = str(dataset.id)
        if file_path.exists():
            file_path.unlink()
        dataset.delete()
        log_audit_event(request.user, "delete_dataset", "InstitutionalDataset", dataset_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        dataset = self.get_object()
        file_path = settings.PROJECT_ROOT / dataset.file_path
        df = pd.read_csv(file_path)

        search = request.query_params.get("search", "").strip().lower()
        if search:
            mask = df.astype(str).apply(lambda col: col.str.lower().str.contains(search, na=False)).any(axis=1)
            df = df[mask]

        sort_by = request.query_params.get("sort_by")
        sort_dir = request.query_params.get("sort_dir", "asc")
        if sort_by and sort_by in df.columns:
            df = df.sort_values(by=sort_by, ascending=(sort_dir != "desc"), kind="mergesort")

        page = max(int(request.query_params.get("page", 1)), 1)
        page_size = min(max(int(request.query_params.get("page_size", 25)), 1), 100)
        total_rows = len(df)
        start = (page - 1) * page_size
        end = start + page_size

        page_df = df.iloc[start:end].where(pd.notna(df.iloc[start:end]), None)
        return Response(
            {
                "dataset_id": str(dataset.id),
                "total_rows": total_rows,
                "page": page,
                "page_size": page_size,
                "columns": list(df.columns),
                "rows": page_df.to_dict(orient="records"),
            }
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="confirm-metadata",
        parser_classes=[JSONParser],
    )
    def confirm_metadata(self, request, pk=None):
        dataset = self.get_object()
        serializer = MetadataConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        overrides = serializer.validated_data["column_overrides"]
        file_path = settings.PROJECT_ROOT / dataset.file_path
        df = pd.read_csv(file_path)
        id_cols = [c for c, t in overrides.items() if t == "id"]
        model_df = df.drop(columns=id_cols, errors="ignore")
        metadata = build_sdv_metadata(
            model_df,
            table_name="records",
            column_overrides={k: v for k, v in overrides.items() if k in model_df.columns and v != "id"},
        )
        dataset.column_overrides = overrides
        dataset.metadata_json = metadata.to_dict()
        dataset.metadata_confirmed = True
        dataset.save(update_fields=["column_overrides", "metadata_json", "metadata_confirmed", "updated_at"])
        log_audit_event(request.user, "confirm_metadata", "InstitutionalDataset", str(dataset.id))
        return Response(InstitutionalDatasetSerializer(dataset).data)


class GenerationJobViewSet(viewsets.ModelViewSet):
    """Create, inspect, rerun, cancel, preview, and download synthetic generation experiments."""

    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        qs = GenerationJob.objects.select_related("dataset", "created_by").all()
        if not self.request.user.is_staff:
            qs = qs.filter(created_by=self.request.user)
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return GenerationJobCreateSerializer
        return GenerationJobSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = serializer.save(created_by=request.user)
        log_audit_event(
            request.user,
            "start_experiment",
            "GenerationJob",
            str(job.id),
            {"model_type": job.model_type, "num_rows": job.num_rows},
        )
        run_generation_experiment_task.delay(str(job.id))
        job.refresh_from_db()
        http_status = (
            status.HTTP_201_CREATED
            if job.status != GenerationJob.Status.FAILED
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        return Response(GenerationJobSerializer(job).data, status=http_status)

    @action(detail=False, methods=["post"])
    def batch(self, request):
        """Launch experiments for multiple selected models using identical configuration."""
        model_types = request.data.get("model_types", ["gaussian_copula", "ctgan", "tvae"])
        created_jobs = []
        for mtype in model_types:
            payload = {**request.data, "model_type": mtype}
            serializer = GenerationJobCreateSerializer(data=payload, context={"request": request})
            serializer.is_valid(raise_exception=True)
            job = serializer.save(created_by=request.user)
            run_generation_experiment_task.delay(str(job.id))
            job.refresh_from_db()
            created_jobs.append(job)
        return Response(GenerationJobSerializer(created_jobs, many=True).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def rerun(self, request, pk=None):
        """Clone an existing experiment into a fresh GenerationJob without overwriting history."""
        source_job = self.get_object()
        new_job = GenerationJob.objects.create(
            dataset=source_job.dataset,
            model_type=source_job.model_type,
            num_rows=source_job.num_rows,
            epochs=source_job.epochs,
            batch_size=source_job.batch_size,
            random_seed=source_job.random_seed,
            model_config=source_job.model_config,
            created_by=request.user,
        )
        run_generation_experiment_task.delay(str(new_job.id))
        new_job.refresh_from_db()
        return Response(GenerationJobSerializer(new_job).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        job = self.get_object()
        if job.status in (GenerationJob.Status.PENDING, GenerationJob.Status.RUNNING):
            job.status = GenerationJob.Status.CANCELLED
            job.save(update_fields=["status"])
        return Response(GenerationJobSerializer(job).data)

    def destroy(self, request, *args, **kwargs):
        job = self.get_object()
        if job.output_file:
            path = settings.PROJECT_ROOT / job.output_file
            if path.exists():
                path.unlink()
        job_id = str(job.id)
        job.delete()
        log_audit_event(request.user, "delete_experiment", "GenerationJob", job_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

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
        log_audit_event(request.user, "download_dataset", "GenerationJob", str(job.id))
        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename=file_path.name,
            content_type="text/csv",
        )

    @action(detail=True, methods=["get"], url_path="report-pdf")
    def report_pdf(self, request, pk=None):
        job = self.get_object()
        if job.status != GenerationJob.Status.COMPLETED:
            return Response(
                {"detail": "Report is only available for completed experiments."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        pdf_bytes = build_experiment_pdf_report(job)
        log_audit_event(request.user, "export_report", "GenerationJob", str(job.id))
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="experiment_{job.id}_report.pdf"'
        return response


class EvaluationResultListView(APIView):
    """List comparative evaluation metrics across all models."""

    def get(self, request):
        queryset = EvaluationResult.objects.all()
        serializer = EvaluationResultSerializer(queryset, many=True)
        return Response(serializer.data)


class RunEvaluationView(APIView):
    """Trigger comparative evaluation and persist updated results."""

    def post(self, request):
        run_comparative_evaluation_task.delay()
        results = EvaluationResult.objects.all()
        serializer = EvaluationResultSerializer(results, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DashboardSummaryView(APIView):
    """Live overview metrics and recent activity scoped to the authenticated user."""

    def get(self, request):
        datasets_qs = InstitutionalDataset.objects.all()
        jobs_qs = GenerationJob.objects.all()
        logs_qs = AuditLog.objects.all()

        if not request.user.is_staff:
            datasets_qs = datasets_qs.filter(owner=request.user)
            jobs_qs = jobs_qs.filter(created_by=request.user)
            logs_qs = logs_qs.filter(user=request.user)

        return Response(
            {
                "total_datasets": datasets_qs.count(),
                "total_experiments": jobs_qs.count(),
                "completed_jobs": jobs_qs.filter(status=GenerationJob.Status.COMPLETED).count(),
                "failed_jobs": jobs_qs.filter(status=GenerationJob.Status.FAILED).count(),
                "latest_evaluations": EvaluationResultSerializer(
                    EvaluationResult.objects.all(), many=True
                ).data,
                "recent_experiments": GenerationJobSerializer(jobs_qs[:5], many=True).data,
                "recent_activity": AuditLogSerializer(logs_qs[:10], many=True).data,
            }
        )
