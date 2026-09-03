from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from .models import Account, Category, RecurringTransaction, Transaction
from .services import generate_due_recurring


class AccountBalanceTests(TestCase):
    def test_balance_is_starting_balance_plus_transactions(self):
        account = Account.objects.create(name="Girokonto", starting_balance=Decimal("100"))
        Transaction.objects.create(account=account, date=date(2026, 9, 1), amount=Decimal("-30"))
        Transaction.objects.create(account=account, date=date(2026, 9, 2), amount=Decimal("50"))
        self.assertEqual(account.balance, Decimal("120"))

    def test_balance_with_no_transactions_equals_starting_balance(self):
        account = Account.objects.create(name="Sparkonto", starting_balance=Decimal("500"))
        self.assertEqual(account.balance, Decimal("500"))


class CategoryRolloverTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create(name="Girokonto", starting_balance=Decimal("0"))
        self.category = Category.objects.create(
            name="Lebensmittel", kind=Category.Kind.VARIABLE, monthly_budget=Decimal("100")
        )
        # Umschlag "existiert" seit drei Monaten vor dem Zielmonat
        self.category.created_at = timezone.make_aware(timezone.datetime(2026, 7, 1))
        self.category.save(update_fields=["created_at"])

    def test_rollover_accumulates_unspent_budget_across_months(self):
        Transaction.objects.create(
            account=self.account, category=self.category, date=date(2026, 7, 15), amount=Decimal("-30")
        )
        Transaction.objects.create(
            account=self.account, category=self.category, date=date(2026, 8, 10), amount=Decimal("-40")
        )
        Transaction.objects.create(
            account=self.account, category=self.category, date=date(2026, 9, 5), amount=Decimal("-10")
        )
        # 3 Monate * 100 Budget - (30+40+10) ausgegeben = 220
        self.assertEqual(self.category.rollover_balance(2026, 9), Decimal("220"))

    def test_rollover_before_category_creation_is_zero(self):
        self.assertEqual(self.category.rollover_balance(2026, 1), Decimal("0"))

    def test_rollover_first_month_equals_month_available(self):
        Transaction.objects.create(
            account=self.account, category=self.category, date=date(2026, 7, 15), amount=Decimal("-30")
        )
        self.assertEqual(self.category.rollover_balance(2026, 7), Decimal("70"))

    def test_available_in_month_ignores_rollover(self):
        Transaction.objects.create(
            account=self.account, category=self.category, date=date(2026, 8, 10), amount=Decimal("-40")
        )
        Transaction.objects.create(
            account=self.account, category=self.category, date=date(2026, 9, 5), amount=Decimal("-10")
        )
        self.assertEqual(self.category.available_in_month(2026, 9), Decimal("90"))


class GenerateDueRecurringTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create(name="Girokonto", starting_balance=Decimal("0"))
        self.category = Category.objects.create(name="Miete", kind=Category.Kind.FIXED, monthly_budget=Decimal("1450"))
        self.recurring = RecurringTransaction.objects.create(
            account=self.account,
            category=self.category,
            description="Mietzins",
            counterparty="Hausverwaltung",
            amount=Decimal("-1450"),
            day_of_month=3,
        )

    def test_generates_transaction_once_day_reached(self):
        created = generate_due_recurring(today=date(2026, 9, 5))
        self.assertEqual(len(created), 1)
        txn = Transaction.objects.get()
        self.assertEqual(txn.amount, Decimal("-1450"))
        self.assertEqual(txn.date, date(2026, 9, 3))
        self.assertEqual(txn.import_ref, "recurring-%d-2026-09" % self.recurring.id)

    def test_not_generated_before_day_of_month(self):
        created = generate_due_recurring(today=date(2026, 9, 1))
        self.assertEqual(created, [])
        self.assertEqual(Transaction.objects.count(), 0)

    def test_running_twice_in_same_month_does_not_duplicate(self):
        generate_due_recurring(today=date(2026, 9, 5))
        created_again = generate_due_recurring(today=date(2026, 9, 20))
        self.assertEqual(created_again, [])
        self.assertEqual(Transaction.objects.count(), 1)

    def test_inactive_recurring_is_skipped(self):
        self.recurring.is_active = False
        self.recurring.save(update_fields=["is_active"])
        created = generate_due_recurring(today=date(2026, 9, 5))
        self.assertEqual(created, [])

    def test_generates_again_in_a_new_month(self):
        generate_due_recurring(today=date(2026, 9, 5))
        created_october = generate_due_recurring(today=date(2026, 10, 5))
        self.assertEqual(len(created_october), 1)
        self.assertEqual(Transaction.objects.count(), 2)


class LoginRequiredTests(TestCase):
    def test_dashboard_redirects_anonymous_user_to_login(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_dashboard_reachable_when_logged_in(self):
        User.objects.create_user(username="tester", password="testpass12345")
        self.client.login(username="tester", password="testpass12345")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
