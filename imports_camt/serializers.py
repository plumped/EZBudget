from rest_framework import serializers

from .models import ImportBatch


class ImportBatchSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = ImportBatch
        fields = [
            "id", "account", "account_name", "filename", "imported_at",
            "transactions_created", "transactions_skipped",
        ]
        read_only_fields = fields
