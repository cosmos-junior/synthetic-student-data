"""URL routing for the datasets REST API."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DashboardSummaryView,
    EvaluationResultListView,
    GenerationJobViewSet,
    HealthCheckView,
    InstitutionalDatasetViewSet,
    LogoutView,
    ProfileView,
    RegisterView,
    RunEvaluationView,
)

router = DefaultRouter()
router.register("datasets", InstitutionalDatasetViewSet, basename="institutional-dataset")
router.register("jobs", GenerationJobViewSet, basename="generation-job")

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", ProfileView.as_view(), name="auth-profile"),
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("evaluations/", EvaluationResultListView.as_view(), name="evaluation-list"),
    path("evaluations/run/", RunEvaluationView.as_view(), name="evaluation-run"),
    path("", include(router.urls)),
]
