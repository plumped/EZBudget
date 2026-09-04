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


class CategoryBudgetHistoryTests(TestCase):
    """save() schreibt bei Anlage und bei jeder echten Budgetänderung einen
    Historie-Eintrag — Grundlage für rückwirkend korrekte Übertragsberechnung."""

    def setUp(self):
        self.category = Category.objects.create(
            name="Lebensmittel", kind=Category.Kind.VARIABLE, monthly_budget=Decimal("100")
        )

    def test_creation_records_one_history_entry_matching_current_budget_period(self):
        year, month = budget_period_for_date(date.today())
        self.assertEqual(self.category.budget_history.count(), 1)
        entry = self.category.budget_history.get()
        self.assertEqual((entry.year, entry.month), (year, month))
        self.assertEqual(entry.monthly_budget, Decimal("100"))

    def test_changing_budget_within_same_period_updates_existing_entry(self):
        self.category.monthly_budget = Decimal("150")
        self.category.save()
        self.assertEqual(self.category.budget_history.count(), 1)
        self.assertEqual(self.category.budget_history.get().monthly_budget, Decimal("150"))

    def test_unrelated_field_change_does_not_touch_history(self):
        self.category.name = "Essen"
        self.category.save()
        self.assertEqual(self.category.budget_history.count(), 1)
        self.assertEqual(self.category.budget_history.get().monthly_budget, Decimal("100"))


class CategoryLegacyBudgetHistoryTests(TestCase):
    """Kategorien, die schon vor diesem Feature existierten, haben noch keine
    Historie — der erste Budgetwechsel danach muss sich selbst heilen, indem er
    den alten Wert rückwirkend am Erstellungsmonat verankert."""

    def setUp(self):
        self.category = Category.objects.create(
            name="Lebensmittel", kind=Category.Kind.VARIABLE, monthly_budget=Decimal("100")
        )
        self.category.created_at = timezone.make_aware(timezone.datetime(2026, 7, 1))
        self.category.save(update_fields=["created_at"])
        self.category.budget_history.all().delete()

    def test_first_budget_change_backfills_creation_month_with_old_value(self):
        self.category.monthly_budget = Decimal("150")
        self.category.save()
        entries = list(self.category.budget_history.order_by("year", "month"))
        self.assertEqual(len(entries), 2)
        self.assertEqual((entries[0].year, entries[0].month), (2026, 7))
        self.assertEqual(entries[0].monthly_budget, Decimal("100"))
        self.assertEqual(entries[1].monthly_budget, Decimal("150"))


class CategoryBudgetForMonthTests(TestCase):
    """budget_for_month()/rollover_balance()/progress_percent() müssen rückwirkend
    mit dem historisch gültigen statt dem aktuellen Budget rechnen."""

    def setUp(self):
        self.account = Account.objects.create(name="Girokonto", starting_balance=Decimal("0"))
        self.category = Category.objects.create(
            name="Lebensmittel", kind=Category.Kind.VARIABLE, monthly_budget=Decimal("150")
        )
        self.category.created_at = timezone.make_aware(timezone.datetime(2026, 7, 1))
        self.category.save(update_fields=["created_at"])
        # Historie unabhängig vom tatsächlichen Testlaufdatum deterministisch nachbilden:
        # 100 ab Juli, Wechsel auf 150 ab August.
        self.category.budget_history.all().delete()
        self.category._record_budget_history(Decimal("100"), ref_date=date(2026, 7, 1))
        self.category._record_budget_history(Decimal("150"), ref_date=date(2026, 8, 1))

    def test_budget_for_month_before_change_uses_old_value(self):
        self.assertEqual(self.category.budget_for_month(2026, 7), Decimal("100"))

    def test_budget_for_month_after_change_uses_new_value(self):
        self.assertEqual(self.category.budget_for_month(2026, 8), Decimal("150"))
        self.assertEqual(self.category.budget_for_month(2026, 9), Decimal("150"))

    def test_rollover_balance_uses_historical_budget_per_month(self):
        Transaction.objects.create(
            account=self.account, category=self.category, date=date(2026, 7, 15), amount=Decimal("-20")
        )
        Transaction.objects.create(
            account=self.account, category=self.category, date=date(2026, 8, 10), amount=Decimal("-30")
        )
        # Juli: 100 Budget - 20 = 80. Plus August: 150 Budget - 30 = 120 -> kumuliert 200.
        self.assertEqual(self.category.rollover_balance(2026, 8), Decimal("200"))

    def test_progress_percent_uses_historical_budget(self):
        Transaction.objects.create(
            account=self.account, category=self.category, date=date(2026, 7, 15), amount=Decimal("-50")
        )
        # Juli-Budget war 100 -> 50%, nicht 150 -> 33%.
        self.assertEqual(self.category.progress_percent(2026, 7), 50)


class CategoryHistoryAndTargetApiTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="tester", password="testpass12345")
        self.client.login(username="tester", password="testpass12345")

    def test_budget_history_and_target_progress_exposed_via_api(self):
        response = self.client.post(
            "/api/categories/",
            {
                "name": "Ferien", "kind": "savings", "monthly_budget": "200",
                "target_amount": "1000", "target_date": "2026-12-31",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(len(data["budget_history"]), 1)
        self.assertEqual(data["budget_history"][0]["monthly_budget"], "200.00")
        self.assertEqual(data["target_amount"], "1000.00")
        self.assertEqual(data["target_date"], "2026-12-31")
        self.assertEqual(data["target_progress_percent"], 20)

    def test_target_progress_percent_none_without_target(self):
        response = self.client.post(
            "/api/categories/",
            {"name": "Diverses", "kind": "variable", "monthly_budget": "50"},
            content_type="application/json",
        )
        self.assertIsNone(response.json()["target_progress_percent"])


class TransferApiTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="tester", password="testpass12345")
        self.client.login(username="tester", password="testpass12345")
        self.checking = Account.objects.create(name="Girokonto", starting_balance=Decimal("1000"))
        self.savings = Account.objects.create(name="Sparkonto", starting_balance=Decimal("0"))

    def test_transfer_creates_two_linked_transactions(self):
        response = self.client.post(
            "/api/transfers/",
            {"from_account": self.checking.id, "to_account": self.savings.id, "amount": "200", "date": "2026-09-05"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Transaction.objects.count(), 2)
        out_txn = Transaction.objects.get(account=self.checking)
        in_txn = Transaction.objects.get(account=self.savings)
        self.assertEqual(out_txn.amount, Decimal("-200"))
        self.assertEqual(in_txn.amount, Decimal("200"))
        self.assertEqual(out_txn.transfer_pair_id, in_txn.id)
        self.assertEqual(in_txn.transfer_pair_id, out_txn.id)
        self.assertTrue(out_txn.is_transfer)
        self.assertIsNone(out_txn.category_id)
        self.checking.refresh_from_db()
        self.savings.refresh_from_db()
        self.assertEqual(self.checking.balance, Decimal("800"))
        self.assertEqual(self.savings.balance, Decimal("200"))

    def test_transfer_rejects_same_account(self):
        response = self.client.post(
            "/api/transfers/",
            {"from_account": self.checking.id, "to_account": self.checking.id, "amount": "50", "date": "2026-09-05"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_deleting_one_leg_deletes_both(self):
        response = self.client.post(
            "/api/transfers/",
            {"from_account": self.checking.id, "to_account": self.savings.id, "amount": "200", "date": "2026-09-05"},
            content_type="application/json",
        )
        out_id = response.json()["out"]["id"]
        response = self.client.delete(f"/api/transactions/{out_id}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_transfer_excluded_from_dashboard_income_and_expense_totals(self):
        self.client.post(
            "/api/transfers/",
            {"from_account": self.checking.id, "to_account": self.savings.id, "amount": "200", "date": "2026-09-05"},
            content_type="application/json",
        )
        response = self.client.get("/api/dashboard/", {"year": 2026, "month": 9})
        data = response.json()
        self.assertEqual(data["income_total"], "0")
        self.assertEqual(data["expense_total"], "0")


class RecurringFrequencyTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create(name="Girokonto", starting_balance=Decimal("0"))

    def test_monthly_import_ref_format_unchanged_for_backward_compatibility(self):
        rt = RecurringTransaction.objects.create(
            account=self.account, description="Miete", amount=Decimal("-1000"), day_of_month=3
        )
        created = generate_due_recurring(today=date(2026, 9, 5))
        self.assertEqual(created[0].import_ref, f"recurring-{rt.id}-2026-09")

    def test_weekly_recurring_generates_on_matching_weekday_only(self):
        RecurringTransaction.objects.create(
            account=self.account, description="Fitness", amount=Decimal("-20"),
            frequency=RecurringTransaction.Frequency.WEEKLY, weekday=0,
        )
        # 2026-09-07 ist ein Montag.
        self.assertEqual(len(generate_due_recurring(today=date(2026, 9, 7))), 1)
        self.assertEqual(generate_due_recurring(today=date(2026, 9, 7)), [])  # kein Duplikat in derselben Woche
        self.assertEqual(generate_due_recurring(today=date(2026, 9, 8)), [])  # Dienstag -> nicht fällig
        self.assertEqual(len(generate_due_recurring(today=date(2026, 9, 14))), 1)  # Folgewoche wieder fällig

    def test_biweekly_recurring_generates_every_other_matching_weekday(self):
        RecurringTransaction.objects.create(
            account=self.account, description="Reinigung", amount=Decimal("-50"),
            frequency=RecurringTransaction.Frequency.BIWEEKLY, weekday=0, start_date=date(2026, 9, 7),
        )
        self.assertEqual(len(generate_due_recurring(today=date(2026, 9, 7))), 1)  # Woche 0 (Anker) -> fällig
        self.assertEqual(generate_due_recurring(today=date(2026, 9, 14)), [])  # Woche 1 -> aus
        self.assertEqual(len(generate_due_recurring(today=date(2026, 9, 21))), 1)  # Woche 2 -> wieder fällig

    def test_yearly_recurring_generates_only_in_target_month_and_repeats_next_year(self):
        RecurringTransaction.objects.create(
            account=self.account, description="Versicherung", amount=Decimal("-300"),
            frequency=RecurringTransaction.Frequency.YEARLY, month_of_year=3, day_of_month=15,
        )
        self.assertEqual(generate_due_recurring(today=date(2026, 2, 20)), [])
        created = generate_due_recurring(today=date(2026, 3, 20))
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].date, date(2026, 3, 15))
        created_next_year = generate_due_recurring(today=date(2027, 3, 20))
        self.assertEqual(len(created_next_year), 1)


class TransactionFilterTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="tester", password="testpass12345")
        self.client.login(username="tester", password="testpass12345")
        self.account = Account.objects.create(name="Girokonto")
        Transaction.objects.create(
            account=self.account, date=date(2026, 7, 5), amount=Decimal("-20"),
            description="Migros Einkauf", counterparty="Migros AG",
        )
        Transaction.objects.create(
            account=self.account, date=date(2026, 9, 5), amount=Decimal("-30"),
            description="Coop Einkauf", counterparty="Coop",
        )

    def test_search_matches_description_or_counterparty_case_insensitively(self):
        response = self.client.get("/api/transactions/", {"search": "migros"})
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["description"], "Migros Einkauf")

    def test_date_range_overrides_month_filter_and_spans_multiple_months(self):
        response = self.client.get(
            "/api/transactions/", {"year": 2026, "month": 9, "date_from": "2026-07-01", "date_to": "2026-07-31"}
        )
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["description"], "Migros Einkauf")

    def test_date_from_only_is_open_ended(self):
        response = self.client.get("/api/transactions/", {"date_from": "2026-08-01"})
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["description"], "Coop Einkauf")
