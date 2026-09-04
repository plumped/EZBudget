from django.contrib import admin

from .models import ImportBatch, Rule


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = ("filename", "account", "imported_at", "transactions_created", "transactions_skipped")
    list_filter = ("account",)


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = (
        "name", "description_value", "counterparty_value", "amount_min", "amount_max",
        "category", "priority", "is_active",
    )
    list_filter = ("is_active",)
