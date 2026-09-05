from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import api_views

router = DefaultRouter()
router.register("", api_views.DebtViewSet, basename="debt")

urlpatterns = [
    path("payoff/", api_views.PayoffSimulationView.as_view(), name="api_payoff"),
    path("sweep-proposal/", api_views.SweepProposalView.as_view(), name="api_sweep_proposal"),
    path("", include(router.urls)),
]
