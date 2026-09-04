from django.db import models


class Rule(models.Model):
    """Regel zur automatischen Umschlag-Zuordnung beim CAMT.053-Import.

    Wird vor der einfachen, stichwortbasierten Category.keywords-Zuordnung
    geprüft (nach Priorität absteigend) — die erste zutreffende Regel gewinnt.
    """

    class Field(models.TextChoices):
        DESCRIPTION = "description", "Beschreibung"
        COUNTERPARTY = "counterparty", "Gegenpartei"
        EITHER = "either", "Beschreibung oder Gegenpartei"

    class MatchType(models.TextChoices):
        CONTAINS = "contains", "enthält"
        STARTSWITH = "startswith", "beginnt mit"
        EXACT = "exact", "ist genau"

    name = models.CharField(max_length=150, blank=True, help_text="Optionaler Name zur Übersicht")
    field = models.CharField(max_length=20, choices=Field.choices, default=Field.EITHER)
    match_type = models.CharField(max_length=20, choices=MatchType.choices, default=MatchType.CONTAINS)
    value = models.CharField(max_length=200, help_text="Text, nach dem gesucht wird (Gross-/Kleinschreibung egal)")
    category = models.ForeignKey("core.Category", on_delete=models.CASCADE, related_name="import_rules")
    priority = models.PositiveIntegerField(default=0, help_text="Höhere Zahl wird zuerst geprüft")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-priority", "id"]

    def __str__(self):
        return f"{self.name or self.value} → {self.category.name}"

    def matches(self, description, counterparty):
        needle = self.value.strip().lower()
        if not needle:
            return False
        haystacks = {
            self.Field.DESCRIPTION: description or "",
            self.Field.COUNTERPARTY: counterparty or "",
            self.Field.EITHER: f"{description or ''} {counterparty or ''}",
        }
        haystack = haystacks[self.field].strip().lower()
        if self.match_type == self.MatchType.CONTAINS:
            return needle in haystack
        if self.match_type == self.MatchType.STARTSWITH:
            return haystack.startswith(needle)
        if self.match_type == self.MatchType.EXACT:
            return haystack == needle
        return False


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
