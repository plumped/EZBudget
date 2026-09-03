from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("envelopes/", views.envelope_list, name="envelope_list"),
    path("envelopes/add/", views.envelope_add, name="envelope_add"),
    path("envelopes/<int:pk>/", views.envelope_detail, name="envelope_detail"),
    path("envelopes/<int:pk>/edit/", views.envelope_edit, name="envelope_edit"),
    path("envelopes/<int:pk>/archive/", views.envelope_archive_toggle, name="envelope_archive_toggle"),
    path("transactions/", views.transaction_list, name="transaction_list"),
    path("transactions/add/", views.transaction_add, name="transaction_add"),
    path("transactions/<int:pk>/delete/", views.transaction_delete, name="transaction_delete"),
    path("accounts/", views.account_list, name="account_list"),
    path("accounts/add/", views.account_add, name="account_add"),
    path("accounts/<int:pk>/", views.account_detail, name="account_detail"),
    path("accounts/<int:pk>/edit/", views.account_edit, name="account_edit"),
    path("accounts/<int:pk>/archive/", views.account_archive_toggle, name="account_archive_toggle"),
    path("recurring/", views.recurring_list, name="recurring_list"),
    path("recurring/add/", views.recurring_add, name="recurring_add"),
    path("recurring/<int:pk>/edit/", views.recurring_edit, name="recurring_edit"),
    path("recurring/<int:pk>/delete/", views.recurring_delete, name="recurring_delete"),
    path("recurring/generate/", views.recurring_generate, name="recurring_generate"),
]
