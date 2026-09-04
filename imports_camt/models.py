from django.db import models


def _text_matches(haystack, match_type, needle):
    haystack = (haystack or "").strip().lower()
    needle = needle.strip().lower()
    if match_type == Rule.MatchType.STARTSWITH:
        return haystack.startswith(needle)
    if match_type == Rule.MatchType.EXACT:
        return haystack == needle
    return needle in haystack


class Rule(models.Model):
    """Regel zur automatischen Umschlag-Zuordnung beim CAMT.053-Import — und
    optional rückwirkend auf bestehende Buchungen anwendbar (siehe api_views).

    Beschreibung, Gegenpartei und Betrag sind unabhängige, optionale
    Bedingungen: nur gesetzte Bedingungen werden geprüft, und ALLE gesetzten
    müssen zutreffen (UND-Verknüpfung). Wird vor der einfachen, stichwort-
    basierten Category.keywords-Zuordnung geprüft (nach Priorität absteigend)
    — die erste zutreffende Regel gewinnt.
    """

    class MatchType(models.TextChoices):
        CONTAINS = "contains", "enthält"
        STARTSWITH = "startswith", "beginnt mit"
        EXACT = "exact", "ist genau"

    name = models.CharField(max_length=150, blank=True, help_text="Optionaler Name zur Übersicht")
    description_match_type = models.CharField(max_length=20, choices=MatchType.choices, default=MatchType.CONTAINS)
    description_value = models.CharField(max_length=200, blank=True, help_text="Leer lassen, um Beschreibung nicht zu prüfen")
    counterparty_match_type = models.CharField(max_length=20, choices=MatchType.choices, default=MatchType.CONTAINS)
    counterparty_value = models.CharField(max_length=200, blank=True, help_text="Leer lassen, um Gegenpartei nicht zu prüfen")
    amount_min = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, help_text="Leer lassen für keine Untergrenze"
    )
    amount_max = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, help_text="Leer lassen für keine Obergrenze"
    )
    category = models.ForeignKey("core.Category", on_delete=models.CASCADE, related_name="import_rules")
    priority = models.PositiveIntegerField(default=0, help_text="Höhere Zahl wird zuerst geprüft")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-priority", "id"]

    def __str__(self):
        return f"{self.name or ('Regel #' + str(self.pk))} → {self.category.name}"

    def has_condition(self):
        return bool(self.description_value or self.counterparty_value or self.amount_min is not None or self.amount_max is not None)

    def matches(self, description, counterparty, amount):
        if not self.has_condition():
            return False
        if self.description_value and not _text_matches(description, self.description_match_type, self.description_value):
            return False
        if self.counterparty_value and not _text_matches(counterparty, self.counterparty_match_type, self.counterparty_value):
            return False
        if self.amount_min is not None and amount < self.amount_min:
            return False
        if self.amount_max is not None and amount > self.amount_max:
            return False
        return True


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
