from django.contrib import admin

from .models import ImportBatch, Rule


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = ("filename", "account", "imported_at", "transactions_created", "transactions_skipped")
    list_filter = ("account",)


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ("name", "field", "match_type", "value", "category", "priority", "is_active")
    list_filter = ("field", "match_type", "is_active")
