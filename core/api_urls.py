from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import api_views

router = DefaultRouter()
router.register("accounts", api_views.AccountViewSet, basename="account")
router.register("categories", api_views.CategoryViewSet, basename="category")
router.register("transactions", api_views.TransactionViewSet, basename="transaction")
router.register("recurring", api_views.RecurringTransactionViewSet, basename="recurring")

urlpatterns = [
    path("auth/csrf/", api_views.CsrfView.as_view(), name="api_csrf"),
    path("auth/signup/", api_views.SignupView.as_view(), name="api_signup"),
    path("auth/login/", api_views.LoginView.as_view(), name="api_login"),
    path("auth/logout/", api_views.LogoutView.as_view(), name="api_logout"),
    path("auth/me/", api_views.MeView.as_view(), name="api_me"),
    path("dashboard/", api_views.DashboardView.as_view(), name="api_dashboard"),
    path("settings/", api_views.SettingsView.as_view(), name="api_settings"),
    path("transfers/", api_views.TransferView.as_view(), name="api_transfer"),
    path("", include(router.urls)),
]
