from django.db import models


class ImportBatch(models.Model):
    account = models.ForeignKey("core.Account", on_delete=models.CASCADE, related_name="import_batches")
    filename = models.CharField(max_length=255)
    imported_at = models.DateTimeField(auto_now_add=True)
    transactions_created = models.PositiveIntegerField(default=0)
    transactions_skipped = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-imported_at"]

    def __str__(self):
        return f"{self.filename} ({self.imported_at:%Y-%m-%d %H:%M})"
