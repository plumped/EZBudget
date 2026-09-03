from django.contrib import admin

from .models import Debt, DebtPayment


class DebtPaymentInline(admin.TabularInline):
    model = DebtPayment
    extra = 0


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = ("name", "creditor", "current_balance", "interest_rate", "minimum_payment", "is_paid_off")
    list_filter = ("is_paid_off",)
    inlines = [DebtPaymentInline]


@admin.register(DebtPayment)
class DebtPaymentAdmin(admin.ModelAdmin):
    list_display = ("debt", "date", "amount", "note")
    list_filter = ("debt",)
