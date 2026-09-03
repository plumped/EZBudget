from datetime import date

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Account, Category, RecurringTransaction, Transaction


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

    class Meta:
        model = Category
        fields = [
            "id", "name", "kind", "monthly_budget", "keywords", "color", "icon",
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


class TransactionSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    category_color = serializers.CharField(source="category.color", read_only=True, default=None)
    category_icon = serializers.CharField(source="category.icon", read_only=True, default=None)
    is_expense = serializers.BooleanField(read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id", "account", "account_name", "category", "category_name", "category_color",
            "category_icon", "date", "amount", "description", "counterparty", "import_ref",
            "is_expense", "created_at",
        ]
        read_only_fields = ["id", "import_ref", "created_at"]


class RecurringTransactionSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    category_color = serializers.CharField(source="category.color", read_only=True, default=None)

    class Meta:
        model = RecurringTransaction
        fields = [
            "id", "account", "account_name", "category", "category_name", "category_color",
            "description", "counterparty", "amount", "day_of_month", "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at"]
