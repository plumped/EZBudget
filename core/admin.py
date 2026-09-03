from django.contrib import admin

from .models import Account, Category, RecurringTransaction, Transaction


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "account_type", "iban", "starting_balance", "balance", "is_archived")
    list_filter = ("account_type", "is_archived")
    search_fields = ("name", "iban")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "monthly_budget", "keywords", "is_archived")
    list_filter = ("kind", "is_archived")
    search_fields = ("name", "keywords")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("date", "description", "counterparty", "amount", "account", "category")
    list_filter = ("account", "category")
    search_fields = ("description", "counterparty", "import_ref")
    date_hierarchy = "date"


@admin.register(RecurringTransaction)
class RecurringTransactionAdmin(admin.ModelAdmin):
    list_display = ("description", "amount", "day_of_month", "account", "category", "is_active")
    list_filter = ("is_active", "account", "category")
    search_fields = ("description", "counterparty")
