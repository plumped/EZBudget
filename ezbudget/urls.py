from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.api_urls")),
    path("api/debts/", include("debts.api_urls")),
    path("api/import/", include("imports_camt.api_urls")),
]
