from rest_framework import serializers

from .models import Debt, DebtPayment


class DebtSerializer(serializers.ModelSerializer):
    paid_so_far = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    progress_percent = serializers.IntegerField(read_only=True)

    class Meta:
        model = Debt
        fields = [
            "id", "name", "creditor", "principal", "current_balance", "interest_rate",
            "minimum_payment", "is_paid_off", "created_at", "paid_so_far", "progress_percent",
        ]
        read_only_fields = ["id", "is_paid_off", "created_at"]


class DebtPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DebtPayment
        fields = ["id", "debt", "date", "amount", "note"]
        read_only_fields = ["id"]
