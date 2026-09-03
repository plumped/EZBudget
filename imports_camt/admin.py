from django.contrib import admin

from .models import ImportBatch


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = ("filename", "account", "imported_at", "transactions_created", "transactions_skipped")
    list_filter = ("account",)
