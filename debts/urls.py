from django.urls import path

from . import views

app_name = "debts"

urlpatterns = [
    path("", views.debt_list, name="debt_list"),
    path("add/", views.debt_add, name="debt_add"),
    path("<int:pk>/", views.debt_detail, name="debt_detail"),
    path("<int:pk>/delete/", views.debt_delete, name="debt_delete"),
]
