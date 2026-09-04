from decimal import Decimal

from django.apps import apps
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class BudgetSettings(models.Model):
    """Einzeilige (Singleton) Einstellungen fürs gesamte Haushaltsbudget."""

    month_start_day = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(28)],
        help_text="Tag im Monat, an dem der Budget-Monat beginnt (1 = Kalendermonat).",
    )

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Account(models.Model):
    class AccountType(models.TextChoices):
        CHECKING = "checking", "Girokonto"
        SAVINGS = "savings", "Sparkonto"
        CASH = "cash", "Bargeld"
        CREDIT = "credit", "Kreditkarte"

    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=AccountType.choices, default=AccountType.CHECKING)
    iban = models.CharField(max_length=34, blank=True)
    starting_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def balance(self):
        agg = self.transactions.aggregate(total=models.Sum("amount"))["total"] or Decimal("0")
        return self.starting_balance + agg


class Category(models.Model):
    """Ein Envelope / Budget-Topf."""

    class Kind(models.TextChoices):
        FIXED = "fixed", "Fixkosten"
        VARIABLE = "variable", "Variable Kosten"
        INCOME = "income", "Einnahmen"
        DEBT = "debt", "Schuldentilgung"
        SAVINGS = "savings", "Sparen"

    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.VARIABLE)
    monthly_budget = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    keywords = models.CharField(
        max_length=300,
        blank=True,
        help_text="Komma-getrennte Stichworte für die automatische Zuordnung beim CAMT.053-Import (z.B. 'migros, coop, denner')",
    )
    color = models.CharField(max_length=7, default="#6366f1")
    icon = models.CharField(max_length=10, default="\U0001F4B0")
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["kind", "name"]

    def __str__(self):
        return self.name

    def keyword_list(self):
        return [k.strip().lower() for k in self.keywords.split(",") if k.strip()]

    def spent_in_month(self, year, month):
        from .budget_month import budget_period_bounds

        start, end = budget_period_bounds(year, month)
        agg = self.transactions.filter(
            date__gte=start, date__lte=end, amount__lt=0
        ).aggregate(total=models.Sum("amount"))
        return -(agg["total"] or Decimal("0"))

    def income_in_month(self, year, month):
        from .budget_month import budget_period_bounds

        start, end = budget_period_bounds(year, month)
        agg = self.transactions.filter(
            date__gte=start, date__lte=end, amount__gt=0
        ).aggregate(total=models.Sum("amount"))
        return agg["total"] or Decimal("0")

    def available_in_month(self, year, month):
        return self.monthly_budget - self.spent_in_month(year, month)

    def progress_percent(self, year, month):
        if self.monthly_budget <= 0:
            return 0
        spent = self.spent_in_month(year, month)
        pct = (spent / self.monthly_budget) * 100
        return int(min(pct, 100))

    def rollover_balance(self, year, month):
        """Kumulierter Umschlag-Saldo inkl. Übertrag aus Vormonaten.

        Rechnet seit Anlage des Umschlags (oder dem Zielmonat, falls dieser
        früher liegt) mit dem aktuellen Monatsbudget statt einer historischen
        Budgethöhe — ausreichend für die Übertragslogik, aber keine
        rückwirkend korrekte Budget-Historie.
        """
        from .budget_month import budget_period_bounds, budget_period_for_date, get_month_start_day

        start_day = get_month_start_day()
        target_start, target_end = budget_period_bounds(year, month, start_day)
        if self.created_at:
            creation_year, creation_month = budget_period_for_date(self.created_at.date(), start_day)
        else:
            creation_year, creation_month = year, month
        creation_start, _ = budget_period_bounds(creation_year, creation_month, start_day)
        if target_start < creation_start:
            return Decimal("0")

        months = (target_start.year - creation_start.year) * 12 + (target_start.month - creation_start.month) + 1

        agg = self.transactions.filter(
            date__gte=creation_start, date__lte=target_end, amount__lt=0
        ).aggregate(total=models.Sum("amount"))
        total_spent = -(agg["total"] or Decimal("0"))
        return self.monthly_budget * months - total_spent


class Transaction(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="transactions")
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions"
    )
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Negativ = Ausgabe, positiv = Einnahme")
    description = models.CharField(max_length=500, blank=True)
    counterparty = models.CharField(max_length=255, blank=True)
    import_ref = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.date} | {self.description[:40]} | {self.amount}"

    @property
    def is_expense(self):
        return self.amount < 0

    def _linked_debt(self):
        """Die Schuld, deren Umschlag dieser Buchung zugeordnet ist (falls vorhanden).

        Bewusst eine frische Query über die App-Registry statt self.category.debt:
        die Rückwärts-Relation wird von Django auf dem Category-Objekt gecacht, das
        über mehrere save()-Aufrufe auf derselben Transaction-Instanz hinweg (z.B.
        beim Bearbeiten) veraltete Zwischenstände von current_balance zeigen könnte.
        Kein Import aus der debts-App nötig, um eine Zirkularität zu vermeiden.
        """
        if not self.category_id:
            return None
        Debt = apps.get_model("debts", "Debt")
        return Debt.objects.filter(category_id=self.category_id).first()

    @staticmethod
    def _adjust_debt(debt, delta):
        new_balance = max(debt.current_balance + delta, Decimal("0"))
        debt.current_balance = new_balance
        debt.is_paid_off = new_balance == 0
        debt.save(update_fields=["current_balance", "is_paid_off"])

    def save(self, *args, **kwargs):
        # Vorherigen Stand VOR dem Schreiben laden, damit bei einer Änderung (nicht nur
        # Neuanlage) der alte Beitrag zur verknüpften Schuld rückgängig gemacht werden
        # kann, bevor der neue angewendet wird — deckt auch einen Wechsel des Umschlags
        # weg von oder hin zu einer Schuld ab.
        previous = type(self).objects.filter(pk=self.pk).first() if self.pk else None
        super().save(*args, **kwargs)
        if previous is not None and previous.category_id == self.category_id and previous.amount == self.amount:
            return
        if previous is not None:
            old_debt = previous._linked_debt()
            if old_debt is not None:
                self._adjust_debt(old_debt, -previous.amount)
        new_debt = self._linked_debt()
        if new_debt is not None:
            self._adjust_debt(new_debt, self.amount)

    def delete(self, *args, **kwargs):
        debt = self._linked_debt()
        if debt is not None:
            self._adjust_debt(debt, -self.amount)
        super().delete(*args, **kwargs)


class RecurringTransaction(models.Model):
    """Vorlage für wiederkehrende Buchungen (Fixkosten, Abos, Lohn ...)."""

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="recurring_transactions")
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="recurring_transactions"
    )
    description = models.CharField(max_length=500)
    counterparty = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Negativ = Ausgabe, positiv = Einnahme")
    day_of_month = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(28)],
        help_text="Tag im Monat, an dem die Buchung generiert wird (1–28, damit jeder Monat den Tag hat)",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["day_of_month", "description"]

    def __str__(self):
        return f"{self.description} ({self.amount} am {self.day_of_month}.)"

    def import_ref_for(self, year, month):
        return f"recurring-{self.pk}-{year}-{month:02d}"
