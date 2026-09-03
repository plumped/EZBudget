from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("envelopes/", views.envelope_list, name="envelope_list"),
    path("envelopes/<int:pk>/", views.envelope_detail, name="envelope_detail"),
    path("transactions/", views.transaction_list, name="transaction_list"),
    path("transactions/add/", views.transaction_add, name="transaction_add"),
    path("transactions/<int:pk>/delete/", views.transaction_delete, name="transaction_delete"),
    path("accounts/", views.account_list, name="account_list"),
    path("accounts/<int:pk>/", views.account_detail, name="account_detail"),
]
