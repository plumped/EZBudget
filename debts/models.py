from decimal import Decimal

from django.db import models
from django.urls import reverse


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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-current_balance"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("debts:debt_detail", args=[self.pk])

    @property
    def paid_so_far(self):
        return self.principal - self.current_balance

    @property
    def progress_percent(self):
        if self.principal <= 0:
            return 0
        return int(min(max((self.paid_so_far / self.principal) * 100, 0), 100))


class DebtPayment(models.Model):
    debt = models.ForeignKey(Debt, on_delete=models.CASCADE, related_name="payments")
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.debt.name}: {self.amount} am {self.date}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        debt = self.debt
        new_balance = debt.current_balance - self.amount
        debt.current_balance = max(new_balance, Decimal("0"))
        if debt.current_balance == 0:
            debt.is_paid_off = True
        debt.save(update_fields=["current_balance", "is_paid_off"])
