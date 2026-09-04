from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import api_views

router = DefaultRouter()
router.register("rules", api_views.RuleViewSet, basename="import-rule")

urlpatterns = [
    path("parse/", api_views.ImportParseView.as_view(), name="api_import_parse"),
    path("confirm/", api_views.ImportConfirmView.as_view(), name="api_import_confirm"),
    path("history/", api_views.ImportHistoryView.as_view(), name="api_import_history"),
    path("", include(router.urls)),
]
