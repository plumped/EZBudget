from rest_framework import serializers

from .models import Debt


class DebtSerializer(serializers.ModelSerializer):
    paid_so_far = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    progress_percent = serializers.IntegerField(read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    account_name = serializers.CharField(source="account.name", read_only=True, default=None)

    class Meta:
        model = Debt
        fields = [
            "id", "name", "creditor", "principal", "current_balance", "interest_rate",
            "minimum_payment", "max_extra_payment", "is_paid_off", "category", "category_name", "account",
            "account_name", "created_at", "paid_so_far", "progress_percent",
        ]
        read_only_fields = ["id", "is_paid_off", "category", "created_at"]
