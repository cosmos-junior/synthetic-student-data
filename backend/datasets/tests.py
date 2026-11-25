"""API and workflow tests for the datasets backend."""

from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import EvaluationResult, GenerationJob


class DatasetAPITests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="researcher", password="secure-password-123")

    def test_health_check_is_public(self):
        response = self.client.get(reverse("health-check"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ok")

    def test_jobs_require_authentication(self):
        response = self.client.get(reverse("generation-job-list"))
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_create_gaussian_copula_job_preview_and_download(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse("generation-job-list"),
            {"model_type": "gaussian_copula", "num_rows": 25},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "completed")
        self.assertTrue(response.data["validation_passed"])
        self.assertEqual(response.data["summary_stats"]["num_records"], 25)

        job_id = response.data["id"]
        preview_resp = self.client.get(reverse("generation-job-preview", args=[job_id]), {"limit": 5})
        self.assertEqual(preview_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(preview_resp.data["total_rows"], 25)
        self.assertEqual(len(preview_resp.data["rows"]), 5)

        download_resp = self.client.get(reverse("generation-job-download", args=[job_id]))
        self.assertEqual(download_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(download_resp["Content-Type"], "text/csv")
        download_resp.close()

        # Clean up test-generated job CSV
        job = GenerationJob.objects.get(id=job_id)
        output_path = Path(settings.PROJECT_ROOT) / job.output_file
        if output_path.exists():
            output_path.unlink()

    def test_ctgan_batch_size_validation(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse("generation-job-list"),
            {"model_type": "ctgan", "num_rows": 50, "batch_size": 35},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("batch_size", response.data)

    def test_evaluation_list_returns_saved_results(self):
        EvaluationResult.objects.create(
            model_name="Gaussian Copula",
            quality_overall=0.9354,
            column_shapes=0.9548,
            column_pair_trends=0.9161,
            data_validity=1.0,
            data_structure=1.0,
            new_row_synthesis=1.0,
            dcr_baseline_protection=0.1916,
            disclosure_protection=0.8648,
            status_accuracy=0.85,
            status_macro_f1=0.6789,
            final_score_r2=0.5824,
            final_score_rmse=8.6615,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("evaluation-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["model_name"], "Gaussian Copula")

