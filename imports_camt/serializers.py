from rest_framework import serializers

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


class RuleSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_color = serializers.CharField(source="category.color", read_only=True)

    class Meta:
        model = Rule
        fields = [
            "id", "name", "field", "match_type", "value", "category", "category_name", "category_color",
            "priority", "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_value(self, value):
        if not value.strip():
            raise serializers.ValidationError("Darf nicht leer sein.")
        return value
