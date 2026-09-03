from django.urls import path

from . import api_views

urlpatterns = [
    path("parse/", api_views.ImportParseView.as_view(), name="api_import_parse"),
    path("confirm/", api_views.ImportConfirmView.as_view(), name="api_import_confirm"),
    path("history/", api_views.ImportHistoryView.as_view(), name="api_import_history"),
]
