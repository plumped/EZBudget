from django.urls import path

from . import views

app_name = "imports"

urlpatterns = [
    path("", views.import_upload, name="import_upload"),
    path("preview/", views.import_preview, name="import_preview"),
    path("cancel/", views.import_cancel, name="import_cancel"),
    path("history/", views.import_history, name="import_history"),
]
