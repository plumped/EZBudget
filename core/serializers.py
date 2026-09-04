from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Account, BudgetSettings, Category, RecurringTransaction, Transaction


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def create(self, validated_data):
        user = User(username=validated_data["username"], email=validated_data.get("email", ""))
        user.set_password(validated_data["password"])
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class BudgetSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetSettings
        fields = ["month_start_day"]


class AccountSerializer(serializers.ModelSerializer):
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Account
        fields = [
            "id", "name", "account_type", "iban", "starting_balance",
            "is_archived", "balance", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


def _year_month_from_context(context):
    request = context.get("request")
    today = date.today()
    if request is None:
        return today.year, today.month
    try:
        year = int(request.query_params.get("year", today.year))
        month = int(request.query_params.get("month", today.month))
    except (TypeError, ValueError):
        year, month = today.year, today.month
    return year, month


class CategorySerializer(serializers.ModelSerializer):
    """Umschlag inkl. Monatswerten (spent/available/rollover/progress) für
    das über ?year=&month= angefragte Monat (Default: heute)."""

    spent = serializers.SerializerMethodField()
    available = serializers.SerializerMethodField()
    rollover = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    target_progress_percent = serializers.SerializerMethodField()
    budget_history = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id", "name", "kind", "monthly_budget", "keywords", "color", "icon",
            "target_amount", "target_date", "target_progress_percent", "budget_history",
            "is_archived", "created_at", "spent", "available", "rollover", "progress",
        ]
        read_only_fields = ["id", "created_at"]

    def get_spent(self, obj):
        year, month = _year_month_from_context(self.context)
        return str(obj.spent_in_month(year, month))

    def get_available(self, obj):
        year, month = _year_month_from_context(self.context)
        return str(obj.available_in_month(year, month))

    def get_rollover(self, obj):
        year, month = _year_month_from_context(self.context)
        return str(obj.rollover_balance(year, month))

    def get_progress(self, obj):
        year, month = _year_month_from_context(self.context)
        return obj.progress_percent(year, month)

    def get_target_progress_percent(self, obj):
        if not obj.target_amount or obj.target_amount <= 0:
            return None
        year, month = _year_month_from_context(self.context)
        pct = (obj.rollover_balance(year, month) / obj.target_amount) * 100
        return int(max(0, min(pct, 100)))

    def get_budget_history(self, obj):
        return [
            {"year": h.year, "month": h.month, "monthly_budget": str(h.monthly_budget)}
            for h in obj.budget_history.order_by("-year", "-month")
        ]


class TransactionSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    category_color = serializers.CharField(source="category.color", read_only=True, default=None)
    category_icon = serializers.CharField(source="category.icon", read_only=True, default=None)
    is_expense = serializers.BooleanField(read_only=True)
    is_transfer = serializers.BooleanField(read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id", "account", "account_name", "category", "category_name", "category_color",
            "category_icon", "date", "amount", "description", "counterparty", "import_ref",
            "is_expense", "is_transfer", "transfer_pair", "created_at",
        ]
        read_only_fields = ["id", "import_ref", "transfer_pair", "created_at"]


class TransferSerializer(serializers.Serializer):
    """Erstellt einen Konto-zu-Konto-Transfer als zwei verknüpfte Buchungen ohne
    Umschlag — siehe TransferView. Kein ModelSerializer, da kein eigenes Modell,
    sondern eine Aktion (analog zu RuleApplySerializer in imports_camt)."""

    from_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    to_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    date = serializers.DateField()
    note = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["from_account"] == attrs["to_account"]:
            raise serializers.ValidationError("Quell- und Zielkonto müssen unterschiedlich sein.")
        return attrs


class RecurringTransactionSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    category_color = serializers.CharField(source="category.color", read_only=True, default=None)

    class Meta:
        model = RecurringTransaction
        fields = [
            "id", "account", "account_name", "category", "category_name", "category_color",
            "description", "counterparty", "amount", "frequency", "day_of_month", "month_of_year",
            "weekday", "start_date", "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at"]
