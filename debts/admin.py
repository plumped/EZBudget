from django.contrib import admin

from .models import Debt


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = ("name", "creditor", "current_balance", "interest_rate", "minimum_payment", "account", "is_paid_off")
    list_filter = ("is_paid_off",)
