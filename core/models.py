from decimal import Decimal

from django.db import models
from django.urls import reverse


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

    def get_absolute_url(self):
        return reverse("core:account_detail", args=[self.pk])


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

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["kind", "name"]

    def __str__(self):
        return self.name

    def keyword_list(self):
        return [k.strip().lower() for k in self.keywords.split(",") if k.strip()]

    def spent_in_month(self, year, month):
        agg = self.transactions.filter(
            date__year=year, date__month=month, amount__lt=0
        ).aggregate(total=models.Sum("amount"))
        return -(agg["total"] or Decimal("0"))

    def income_in_month(self, year, month):
        agg = self.transactions.filter(
            date__year=year, date__month=month, amount__gt=0
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
