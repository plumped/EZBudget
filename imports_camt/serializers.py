from rest_framework import serializers

from core.models import Category

from .models import ImportBatch, Rule


class ImportBatchSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = ImportBatch
        fields = [
            "id", "account", "account_name", "filename", "imported_at",
            "transactions_created", "transactions_skipped",
        ]
        read_only_fields = fields


def _validate_has_condition(data):
    if not data.get("description_value") and not data.get("counterparty_value") and data.get("amount_min") is None and data.get("amount_max") is None:
        raise serializers.ValidationError("Mindestens eine Bedingung angeben (Beschreibung, Gegenpartei oder Betrag).")


class RuleSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_color = serializers.CharField(source="category.color", read_only=True)

    class Meta:
        model = Rule
        fields = [
            "id", "name", "description_match_type", "description_value",
            "counterparty_match_type", "counterparty_value", "amount_min", "amount_max",
            "category", "category_name", "category_color", "priority", "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, data):
        merged = {**(self.instance.__dict__ if self.instance else {}), **data}
        _validate_has_condition(merged)
        return data


class RuleConditionSerializer(serializers.Serializer):
    """Bedingungen einer Regel, unabhängig davon ob sie schon gespeichert ist —
    Basis für die Live-Vorschau ("welche bestehenden Buchungen passen gerade")."""

    description_match_type = serializers.ChoiceField(choices=Rule.MatchType.choices, required=False, default=Rule.MatchType.CONTAINS)
    description_value = serializers.CharField(required=False, allow_blank=True, default="")
    counterparty_match_type = serializers.ChoiceField(choices=Rule.MatchType.choices, required=False, default=Rule.MatchType.CONTAINS)
    counterparty_value = serializers.CharField(required=False, allow_blank=True, default="")
    amount_min = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True, default=None)
    amount_max = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True, default=None)

    def validate(self, data):
        _validate_has_condition(data)
        return data


class RuleApplySerializer(RuleConditionSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
