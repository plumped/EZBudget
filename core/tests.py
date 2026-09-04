from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from .budget_month import budget_period_bounds, budget_period_for_date
from .models import Account, BudgetSettings, Category, RecurringTransaction, Transaction
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


class CustomMonthStartDayTests(TestCase):
    """Budget-Monat kann statt am 1. an einem anderen Tag beginnen (z.B. am 25.,
    wenn Lohn und Daueraufträge dort ausgeführt werden)."""

    def setUp(self):
        BudgetSettings.objects.update_or_create(pk=1, defaults={"month_start_day": 25})
        self.account = Account.objects.create(name="Girokonto", starting_balance=Decimal("0"))
        self.category = Category.objects.create(
            name="Lebensmittel", kind=Category.Kind.VARIABLE, monthly_budget=Decimal("100")
        )
        self.category.created_at = timezone.make_aware(timezone.datetime(2026, 6, 1))
        self.category.save(update_fields=["created_at"])

    def test_budget_period_bounds_shifted(self):
        start, end = budget_period_bounds(2026, 8, start_day=25)
        self.assertEqual(start, date(2026, 8, 25))
        self.assertEqual(end, date(2026, 9, 24))

    def test_budget_period_for_date_before_and_after_start_day(self):
        self.assertEqual(budget_period_for_date(date(2026, 9, 3), start_day=25), (2026, 8))
        self.assertEqual(budget_period_for_date(date(2026, 9, 25), start_day=25), (2026, 9))

    def test_transaction_before_start_day_counts_towards_previous_budget_month(self):
        # 3. September liegt VOR dem 25. -> gehört zum Budget-Monat "August"
        Transaction.objects.create(
            account=self.account, category=self.category, date=date(2026, 9, 3), amount=Decimal("-40")
        )
        self.assertEqual(self.category.spent_in_month(2026, 8), Decimal("40"))
        self.assertEqual(self.category.spent_in_month(2026, 9), Decimal("0"))

    def test_transaction_on_start_day_counts_towards_that_budget_month(self):
        Transaction.objects.create(
            account=self.account, category=self.category, date=date(2026, 9, 25), amount=Decimal("-40")
        )
        self.assertEqual(self.category.spent_in_month(2026, 9), Decimal("40"))
        self.assertEqual(self.category.spent_in_month(2026, 8), Decimal("0"))

    def test_dashboard_and_transactions_api_use_shifted_period(self):
        User.objects.create_user(username="tester", password="testpass12345")
        self.client.login(username="tester", password="testpass12345")
        Transaction.objects.create(
            account=self.account, category=self.category, date=date(2026, 9, 3), amount=Decimal("-40")
        )
        response = self.client.get("/api/transactions/", {"year": 2026, "month": 8})
        self.assertEqual(len(response.json()), 1)
        response = self.client.get("/api/transactions/", {"year": 2026, "month": 9})
        self.assertEqual(len(response.json()), 0)

        response = self.client.get("/api/dashboard/", {"year": 2026, "month": 8})
        data = response.json()
        self.assertEqual(data["period_start"], "2026-08-25")
        self.assertEqual(data["period_end"], "2026-09-24")


class SettingsApiTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="tester", password="testpass12345")
        self.client.login(username="tester", password="testpass12345")

    def test_get_defaults_to_calendar_month(self):
        response = self.client.get("/api/settings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["month_start_day"], 1)

    def test_put_updates_month_start_day(self):
        response = self.client.put(
            "/api/settings/", {"month_start_day": 25}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(BudgetSettings.load().month_start_day, 25)

    def test_put_rejects_out_of_range_value(self):
        response = self.client.put(
            "/api/settings/", {"month_start_day": 31}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)


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
    def test_dashboard_api_rejects_anonymous_user(self):
        response = self.client.get("/api/dashboard/")
        self.assertEqual(response.status_code, 403)

    def test_dashboard_api_reachable_when_logged_in(self):
        User.objects.create_user(username="tester", password="testpass12345")
        self.client.login(username="tester", password="testpass12345")
        response = self.client.get("/api/dashboard/")
        self.assertEqual(response.status_code, 200)


class AuthApiTests(TestCase):
    def test_signup_creates_user_and_logs_in(self):
        response = self.client.post(
            "/api/auth/signup/",
            {"username": "neu", "password": "SuperSecret123!", "email": ""},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username="neu").exists())
        # Session ist direkt eingeloggt
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "neu")

    def test_signup_rejects_weak_password(self):
        response = self.client.post(
            "/api/auth/signup/", {"username": "x", "password": "123"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_login_with_wrong_password_fails(self):
        User.objects.create_user(username="tester", password="testpass12345")
        response = self.client.post(
            "/api/auth/login/", {"username": "tester", "password": "falsch"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_login_then_logout(self):
        User.objects.create_user(username="tester", password="testpass12345")
        response = self.client.post(
            "/api/auth/login/", {"username": "tester", "password": "testpass12345"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post("/api/auth/logout/")
        self.assertEqual(response.status_code, 204)
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 403)


class AccountApiTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="tester", password="testpass12345")
        self.client.login(username="tester", password="testpass12345")

    def test_create_list_and_archive_account(self):
        response = self.client.post(
            "/api/accounts/",
            {"name": "Girokonto", "account_type": "checking", "starting_balance": "100"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        account_id = response.json()["id"]
        self.assertEqual(response.json()["balance"], "100.00")

        response = self.client.get("/api/accounts/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

        response = self.client.post(f"/api/accounts/{account_id}/archive_toggle/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_archived"])

        response = self.client.get("/api/accounts/", {"active_only": "1"})
        self.assertEqual(response.json(), [])


class CategoryApiTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="tester", password="testpass12345")
        self.client.login(username="tester", password="testpass12345")
        self.account = Account.objects.create(name="Girokonto")

    def test_category_exposes_month_computed_fields(self):
        response = self.client.post(
            "/api/categories/",
            {"name": "Lebensmittel", "kind": "variable", "monthly_budget": "300", "color": "#123456", "icon": "🛒"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        category_id = response.json()["id"]

        Transaction.objects.create(
            account=self.account, category_id=category_id, date=date(2026, 9, 5), amount=Decimal("-50")
        )

        response = self.client.get(f"/api/categories/{category_id}/", {"year": 2026, "month": 9})
        data = response.json()
        self.assertEqual(data["spent"], "50")
        self.assertEqual(data["available"], "250.00")


class TransactionApiTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="tester", password="testpass12345")
        self.client.login(username="tester", password="testpass12345")
        self.account = Account.objects.create(name="Girokonto")
        self.category = Category.objects.create(name="Lebensmittel", kind=Category.Kind.VARIABLE)

    def test_create_and_filter_transactions_by_month_and_category(self):
        self.client.post(
            "/api/transactions/",
            {"account": self.account.id, "category": self.category.id, "date": "2026-09-05", "amount": "-20"},
            content_type="application/json",
        )
        self.client.post(
            "/api/transactions/",
            {"account": self.account.id, "date": "2026-08-05", "amount": "-10"},
            content_type="application/json",
        )

        response = self.client.get("/api/transactions/", {"year": 2026, "month": 9, "category": self.category.id})
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["amount"], "-20.00")

    def test_delete_transaction(self):
        response = self.client.post(
            "/api/transactions/",
            {"account": self.account.id, "date": "2026-09-05", "amount": "-20"},
            content_type="application/json",
        )
        txn_id = response.json()["id"]
        response = self.client.delete(f"/api/transactions/{txn_id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Transaction.objects.filter(id=txn_id).exists())

    def test_edit_transaction(self):
        response = self.client.post(
            "/api/transactions/",
            {"account": self.account.id, "category": self.category.id, "date": "2026-09-05", "amount": "-20"},
            content_type="application/json",
        )
        txn_id = response.json()["id"]
        response = self.client.put(
            f"/api/transactions/{txn_id}/",
            {
                "account": self.account.id,
                "category": self.category.id,
                "date": "2026-09-06",
                "amount": "-35",
                "description": "Korrigiert",
                "counterparty": "Migros",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        txn = Transaction.objects.get(id=txn_id)
        self.assertEqual(txn.amount, Decimal("-35"))
        self.assertEqual(txn.description, "Korrigiert")


class RecurringApiTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="tester", password="testpass12345")
        self.client.login(username="tester", password="testpass12345")
        self.account = Account.objects.create(name="Girokonto")

    def test_generate_action_creates_due_transactions(self):
        self.client.post(
            "/api/recurring/",
            {"account": self.account.id, "description": "Abo", "amount": "-9.90", "day_of_month": 1},
            content_type="application/json",
        )
        response = self.client.post("/api/recurring/generate/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["created_count"], 1)
        self.assertEqual(Transaction.objects.count(), 1)
