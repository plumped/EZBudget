from datetime import date
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

    # Fallback, falls kein Icon aus dem Frontend-Katalog gewählt wurde — pro Art,
    # damit neue Umschläge nicht alle pauschal dasselbe Icon zeigen. Werte sind
    # @phosphor-icons/react-Exportnamen (siehe frontend/src/components/iconCatalog.ts),
    # keine Emoji — die App verwendet durchgehend Phosphor-Icons als UI-Chrome.
    KIND_ICON_DEFAULTS = {
        Kind.FIXED: "FileText",
        Kind.VARIABLE: "ShoppingCart",
        Kind.INCOME: "TrendUp",
        Kind.DEBT: "CreditCard",
        Kind.SAVINGS: "PiggyBank",
    }

    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.VARIABLE)
    monthly_budget = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    keywords = models.CharField(
        max_length=300,
        blank=True,
        help_text="Komma-getrennte Stichworte für die automatische Zuordnung beim CAMT.053-Import (z.B. 'migros, coop, denner')",
    )
    color = models.CharField(max_length=7, default="#6366f1")
    icon = models.CharField(
        max_length=32, blank=True, default="",
        help_text="Phosphor-Icon-Name aus dem Frontend-Katalog — bei leerem Wert wird beim Speichern ein zur Art passendes Icon gesetzt.",
    )
    target_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Sparziel — optionaler Zielbetrag, z.B. für einen Sparumschlag.",
    )
    target_date = models.DateField(
        null=True, blank=True, help_text="Optionales Zieldatum, bis wann das Sparziel erreicht sein soll.",
    )
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["kind", "name"]

    def __str__(self):
        return self.name

    def keyword_list(self):
        return [k.strip().lower() for k in self.keywords.split(",") if k.strip()]

    def save(self, *args, **kwargs):
        if not self.icon:
            self.icon = self.KIND_ICON_DEFAULTS.get(self.kind, "\U0001F4B0")

        # Budget-Historie mitschreiben, damit rollover_balance()/budget_for_month()
        # vergangene Monate rückwirkend mit dem damals gültigen Budget statt dem
        # aktuellen rechnen können (siehe CategoryBudgetHistory unten).
        is_new = self.pk is None
        previous_budget = None
        if not is_new:
            previous = type(self).objects.filter(pk=self.pk).only("monthly_budget").first()
            previous_budget = previous.monthly_budget if previous else None
        changed = previous_budget is not None and previous_budget != self.monthly_budget
        super().save(*args, **kwargs)
        if is_new:
            self._record_budget_history(self.monthly_budget)
        elif changed:
            if not self.budget_history.exists():
                # Umschlag existierte schon vor der Budget-Historie-Funktion — Startwert
                # nachträglich an seinem Erstellungsmonat verankern, damit vergangene
                # Monate nicht rückwirkend den gerade neu gesetzten Wert übernehmen.
                creation_date = self.created_at.date() if self.created_at else date.today()
                self._record_budget_history(previous_budget, ref_date=creation_date)
            self._record_budget_history(self.monthly_budget)

    def _record_budget_history(self, amount, ref_date=None):
        from .budget_month import budget_period_for_date, get_month_start_day

        ref_date = ref_date or date.today()
        year, month = budget_period_for_date(ref_date, get_month_start_day())
        CategoryBudgetHistory.objects.update_or_create(
            category=self, year=year, month=month, defaults={"monthly_budget": amount}
        )

    def budget_for_month(self, year, month):
        """Das in `year`/`month` gültige Monatsbudget — historisch korrekt, falls
        sich `monthly_budget` seither geändert hat (siehe CategoryBudgetHistory)."""
        entries = list(self.budget_history.order_by("year", "month"))
        applicable = [h.monthly_budget for h in entries if (h.year, h.month) <= (year, month)]
        return applicable[-1] if applicable else self.monthly_budget

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
        return self.budget_for_month(year, month) - self.spent_in_month(year, month)

    def progress_percent(self, year, month):
        budget = self.budget_for_month(year, month)
        if budget <= 0:
            return 0
        spent = self.spent_in_month(year, month)
        pct = (spent / budget) * 100
        return int(min(pct, 100))

    def rollover_balance(self, year, month):
        """Kumulierter Umschlag-Saldo inkl. Übertrag aus Vormonaten.

        Rechnet seit Anlage des Umschlags (oder dem Zielmonat, falls dieser
        früher liegt) mit dem jeweils historisch gültigen Monatsbudget
        (siehe CategoryBudgetHistory), nicht pauschal mit dem aktuellen.
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

        history = list(self.budget_history.order_by("year", "month"))

        def budget_at(y, m):
            applicable = [h.monthly_budget for h in history if (h.year, h.month) <= (y, m)]
            return applicable[-1] if applicable else self.monthly_budget

        total_budgeted = Decimal("0")
        cy, cm = creation_year, creation_month
        while (cy, cm) <= (year, month):
            total_budgeted += budget_at(cy, cm)
            cy, cm = (cy + 1, 1) if cm == 12 else (cy, cm + 1)

        agg = self.transactions.filter(
            date__gte=creation_start, date__lte=target_end, amount__lt=0
        ).aggregate(total=models.Sum("amount"))
        total_spent = -(agg["total"] or Decimal("0"))
        return total_budgeted - total_spent


class CategoryBudgetHistory(models.Model):
    """Ein Snapshot von `Category.monthly_budget`, gültig ab genau diesem
    Budget-Monat — ermöglicht rückwirkend korrekte Übertrags-/Fortschrittsberechnung
    statt pauschal mit dem aktuellen Budget zu rechnen (siehe Category.save())."""

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="budget_history")
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    monthly_budget = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name_plural = "Category budget history"
        unique_together = ("category", "year", "month")
        ordering = ["year", "month"]

    def __str__(self):
        return f"{self.category} {self.year}-{self.month:02d}: {self.monthly_budget}"


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
    transfer_pair = models.OneToOneField(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="+",
        help_text="Verknüpfte Gegenbuchung, falls dies ein Konto-zu-Konto-Transfer ist.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.date} | {self.description[:40]} | {self.amount}"

    @property
    def is_expense(self):
        return self.amount < 0

    @property
    def is_transfer(self):
        return self.transfer_pair_id is not None

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

    class Frequency(models.TextChoices):
        WEEKLY = "weekly", "Wöchentlich"
        BIWEEKLY = "biweekly", "Alle 2 Wochen"
        MONTHLY = "monthly", "Monatlich"
        YEARLY = "yearly", "Jährlich"

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="recurring_transactions")
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="recurring_transactions"
    )
    description = models.CharField(max_length=500)
    counterparty = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Negativ = Ausgabe, positiv = Einnahme")
    frequency = models.CharField(max_length=10, choices=Frequency.choices, default=Frequency.MONTHLY)
    day_of_month = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(28)],
        help_text="Für monatlich/jährlich: Tag im Monat (1–28, damit jeder Monat den Tag hat).",
    )
    month_of_year = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Für jährlich: Monat im Jahr.",
    )
    weekday = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        help_text="Für wöchentlich/alle 2 Wochen: Wochentag (0=Montag ... 6=Sonntag).",
    )
    start_date = models.DateField(
        default=date.today,
        help_text="Für alle 2 Wochen: Ankerdatum, ab dem der 2-Wochen-Rhythmus gezählt wird.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["description"]

    def __str__(self):
        return f"{self.description} ({self.amount}, {self.get_frequency_display()})"

    def is_due_on(self, target_date):
        """Ob für den Budget-Zeitpunkt `target_date` grundsätzlich eine Buchung
        fällig ist. Bei monatlich/jährlich absichtlich `>=` statt `==`, damit ein
        verpasster Tag innerhalb derselben Periode noch nachgeholt wird (analog zum
        bisherigen Verhalten vor Einführung der weiteren Frequenzen)."""
        if self.frequency == self.Frequency.MONTHLY:
            return target_date.day >= self.day_of_month
        if self.frequency == self.Frequency.YEARLY:
            return target_date.month == self.month_of_year and target_date.day >= self.day_of_month
        if self.frequency == self.Frequency.WEEKLY:
            return target_date.weekday() == self.weekday
        if self.frequency == self.Frequency.BIWEEKLY:
            if target_date.weekday() != self.weekday or target_date < self.start_date:
                return False
            return (target_date - self.start_date).days // 7 % 2 == 0
        return False

    def period_key(self, target_date):
        """Eindeutiger Schlüssel für die Periode, in der `target_date` liegt —
        verhindert Doppel-Generierung pro Periode."""
        if self.frequency == self.Frequency.MONTHLY:
            return f"{target_date.year}-{target_date.month:02d}"
        if self.frequency == self.Frequency.YEARLY:
            return f"{target_date.year}"
        if self.frequency == self.Frequency.WEEKLY:
            iso_year, iso_week, _ = target_date.isocalendar()
            return f"w{iso_year}-{iso_week:02d}"
        if self.frequency == self.Frequency.BIWEEKLY:
            block = (target_date - self.start_date).days // 14
            return f"b{block}"
        return target_date.isoformat()

    def occurrence_date(self, target_date):
        """Das tatsächliche Datum, auf das die Buchung dieser Periode gebucht wird."""
        if self.frequency == self.Frequency.MONTHLY:
            return date(target_date.year, target_date.month, self.day_of_month)
        if self.frequency == self.Frequency.YEARLY:
            return date(target_date.year, self.month_of_year, self.day_of_month)
        return target_date

    def import_ref_for(self, target_date):
        return f"recurring-{self.pk}-{self.period_key(target_date)}"
