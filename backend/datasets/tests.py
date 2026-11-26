"""API, ownership, upload, profiling, and workflow tests for the datasets backend."""

from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import EvaluationResult, GenerationJob, InstitutionalDataset


class DatasetAPITests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="researcher", password="secure-password-123")
        self.other_user = User.objects.create_user(username="other", password="secure-password-456")

    def test_health_check_is_public(self):
        response = self.client.get(reverse("health-check"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ok")

    def test_register_profile_and_logout(self):
        reg_resp = self.client.post(
            reverse("auth-register"),
            {"username": "new_user", "email": "new@example.com", "password": "strongpassword99"},
            format="json",
        )
        self.assertEqual(reg_resp.status_code, status.HTTP_201_CREATED)
        token = reg_resp.data["token"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        me_resp = self.client.get(reverse("auth-profile"))
        self.assertEqual(me_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(me_resp.data["username"], "new_user")

        logout_resp = self.client.post(reverse("auth-logout"))
        self.assertEqual(logout_resp.status_code, status.HTTP_200_OK)

    def test_jobs_require_authentication(self):
        response = self.client.get(reverse("generation-job-list"))
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_dataset_upload_profile_preview_metadata_and_ownership(self):
        self.client.force_authenticate(user=self.user)
        csv_content = (
            b"student_id,age,gender,programme,year_of_study,attendance_percentage,coursework_score,exam_score,final_score,grade,academic_status\n"
            b"IN1700001,20,Male,BIT,2,85,70,80,76.0,A,Pass\n"
            b"IN1700002,22,Female,BCS,3,65,30,35,33.0,E,Fail\n"
        )
        upload = SimpleUploadedFile("sample.csv", csv_content, content_type="text/csv")
        resp = self.client.post(
            reverse("institutional-dataset-list"),
            {
                "file": upload,
                "name": "Sample Student Data",
                "category": "student_academic",
                "authorization_confirmed": "true",
            },
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        dataset_id = resp.data["id"]
        self.assertEqual(resp.data["row_count"], 2)
        self.assertIn("student_id", resp.data["profile_json"]["identifier_candidates"])

        # Preview paginated
        prev_resp = self.client.get(reverse("institutional-dataset-preview", args=[dataset_id]), {"page": 1, "page_size": 1})
        self.assertEqual(prev_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(prev_resp.data["rows"]), 1)

        # Confirm metadata
        confirm_resp = self.client.post(
            reverse("institutional-dataset-confirm-metadata", args=[dataset_id]),
            {"column_overrides": {"student_id": "id", "year_of_study": "ordinal"}},
            format="json",
        )
        self.assertEqual(confirm_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(confirm_resp.data["metadata_confirmed"])

        # Ownership isolation: other_user cannot access this dataset
        self.client.force_authenticate(user=self.other_user)
        other_resp = self.client.get(reverse("institutional-dataset-detail", args=[dataset_id]))
        self.assertEqual(other_resp.status_code, status.HTTP_404_NOT_FOUND)

        # Clean up uploaded file via owner DELETE
        self.client.force_authenticate(user=self.user)
        del_resp = self.client.delete(reverse("institutional-dataset-detail", args=[dataset_id]))
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_create_gaussian_copula_job_preview_download_pdf_and_ownership(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse("generation-job-list"),
            {"model_type": "gaussian_copula", "num_rows": 25, "random_seed": 7},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "completed")
        self.assertTrue(response.data["validation_passed"])
        self.assertIn("fidelity", response.data["evaluation_json"])
        self.assertIn("privacy", response.data["evaluation_json"])

        job_id = response.data["id"]

        # Ownership isolation: other_user cannot view or download this job
        self.client.force_authenticate(user=self.other_user)
        self.assertEqual(
            self.client.get(reverse("generation-job-detail", args=[job_id])).status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.client.force_authenticate(user=self.user)
        preview_resp = self.client.get(reverse("generation-job-preview", args=[job_id]), {"limit": 5})
        self.assertEqual(preview_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(preview_resp.data["rows"]), 5)

        download_resp = self.client.get(reverse("generation-job-download", args=[job_id]))
        self.assertEqual(download_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(download_resp["Content-Type"], "text/csv")
        download_resp.close()

        pdf_resp = self.client.get(reverse("generation-job-report-pdf", args=[job_id]))
        self.assertEqual(pdf_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(pdf_resp["Content-Type"], "application/pdf")

        dash_resp = self.client.get(reverse("dashboard-summary"))
        self.assertEqual(dash_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(dash_resp.data["completed_jobs"], 1)

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
            privacy_risk_label="Moderate observed risk",
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
