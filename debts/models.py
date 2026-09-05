from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import Account, Category


class Debt(models.Model):
    name = models.CharField(max_length=150)
    creditor = models.CharField(max_length=150, blank=True)
    principal = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="Ursprüngliche Kreditsumme / Startbetrag"
    )
    current_balance = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0"), help_text="Jährlicher effektiver Zinssatz in %"
    )
    minimum_payment = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monatliche Mindestrate")
    is_paid_off = models.BooleanField(default=False)
    category = models.OneToOneField(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="debt",
        help_text="Automatisch angelegter Umschlag, über den Buchungen mit dieser Schuld verknüpft werden.",
    )
    account = models.OneToOneField(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="debt",
        help_text=(
            "Optional bei einer laufenden Kreditlinie (z.B. Kreditkarte): das Konto, dessen "
            "Buchungen automatisch die Restschuld verändern — normale Ausgaben erhöhen sie, "
            "Zahlungen (z.B. per Transfer) senken sie. Ohne Verknüpfung bleibt die klassische "
            "manuelle Zahlung über den Umschlag der Weg, die Restschuld zu ändern."
        ),
    )
    last_interest_year = models.PositiveIntegerField(null=True, blank=True)
    last_interest_month = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-current_balance"]

    def __str__(self):
        return self.name

    @property
    def paid_so_far(self):
        return self.principal - self.current_balance

    @property
    def progress_percent(self):
        if self.principal <= 0:
            return 0
        return int(min(max((self.paid_so_far / self.principal) * 100, 0), 100))

    def save(self, *args, **kwargs):
        # Jede Schuld bekommt automatisch einen eigenen Umschlag (Kind "debt"), über den
        # sich Buchungen mit ihr verknüpfen lassen. Name und Archiv-Status bleiben mit der
        # Schuld synchron; das Monatsbudget wird nur bei der Erstellung auf die Mindestrate
        # vorbelegt und danach nicht mehr angetastet, damit es frei änderbar bleibt.
        if self.category_id is None:
            self.category = Category.objects.create(
                name=self.name,
                kind=Category.Kind.DEBT,
                monthly_budget=self.minimum_payment,
                is_archived=self.is_paid_off,
            )
        else:
            Category.objects.filter(pk=self.category_id).update(name=self.name, is_archived=self.is_paid_off)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.category_id:
            Category.objects.filter(pk=self.category_id).update(is_archived=True)
        super().delete(*args, **kwargs)
