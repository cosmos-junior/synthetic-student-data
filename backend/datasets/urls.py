"""URL routing for the datasets REST API."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    EvaluationResultListView,
    GenerationJobViewSet,
    HealthCheckView,
    RunEvaluationView,
)

router = DefaultRouter()
router.register("jobs", GenerationJobViewSet, basename="generation-job")

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("evaluations/", EvaluationResultListView.as_view(), name="evaluation-list"),
    path("evaluations/run/", RunEvaluationView.as_view(), name="evaluation-run"),
    path("", include(router.urls)),
]

