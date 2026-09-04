from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from core.models import Account, Category, Transaction

from .models import Debt
from .services import simulate_payoff


class SimulatePayoffTests(TestCase):
    def test_no_debts_returns_empty_result_immediately(self):
        result = simulate_payoff([], strategy="avalanche")
        self.assertEqual(result.months, 0)
        self.assertEqual(result.total_interest, Decimal("0"))
        self.assertEqual(result.payoff_order, [])
        self.assertEqual(result.schedule, [])

    def test_zero_balance_debts_are_ignored(self):
        debts = [{"id": 1, "name": "Bereits getilgt", "balance": Decimal("0"), "rate": Decimal("5"), "minimum": Decimal("50")}]
        result = simulate_payoff(debts, strategy="avalanche")
        self.assertEqual(result.months, 0)

    def test_avalanche_pays_off_highest_interest_rate_first(self):
        debts = [
            {"id": 1, "name": "Niedrigzins", "balance": Decimal("1000"), "rate": Decimal("2"), "minimum": Decimal("50")},
            {"id": 2, "name": "Hochzins", "balance": Decimal("1000"), "rate": Decimal("20"), "minimum": Decimal("50")},
        ]
        result = simulate_payoff(debts, strategy="avalanche", extra_budget=Decimal("200"))
        self.assertEqual(result.payoff_order[0], "Hochzins")

    def test_snowball_pays_off_smallest_balance_first(self):
        debts = [
            {"id": 1, "name": "Kleine Schuld", "balance": Decimal("300"), "rate": Decimal("2"), "minimum": Decimal("50")},
            {"id": 2, "name": "Grosse Schuld", "balance": Decimal("5000"), "rate": Decimal("20"), "minimum": Decimal("50")},
        ]
        result = simulate_payoff(debts, strategy="snowball", extra_budget=Decimal("200"))
        self.assertEqual(result.payoff_order[0], "Kleine Schuld")

    def test_freed_minimum_payment_rolls_into_next_debt(self):
        """Sobald eine Schuld getilgt ist, fliesst ihre Mindestrate ab dem Folgemonat
        zusätzlich zum Extra-Budget in die nächste Schuld (Schneeball-Effekt) — ohne
        das bräuchte "Grosse Schuld" bei 50/Monat Mindestrate und 10% Zins weit über
        100 Monate, da 25/Monat davon sofort wieder als Zins anfallen."""
        debts = [
            {"id": 1, "name": "Kleine Schuld", "balance": Decimal("300"), "rate": Decimal("0"), "minimum": Decimal("150")},
            {"id": 2, "name": "Grosse Schuld", "balance": Decimal("3000"), "rate": Decimal("10"), "minimum": Decimal("50")},
        ]
        result = simulate_payoff(debts, strategy="avalanche", extra_budget=Decimal("0"))
        self.assertEqual(result.months, 18)

    def test_extra_budget_accelerates_payoff(self):
        debts = [
            {"id": 1, "name": "Kredit", "balance": Decimal("3000"), "rate": Decimal("10"), "minimum": Decimal("100")},
        ]
        without_extra = simulate_payoff(debts, strategy="avalanche", extra_budget=Decimal("0"))
        with_extra = simulate_payoff(debts, strategy="avalanche", extra_budget=Decimal("300"))
        self.assertLess(with_extra.months, without_extra.months)

    def test_interest_accrues_when_only_minimum_is_paid(self):
        debts = [
            {"id": 1, "name": "Kredit", "balance": Decimal("1000"), "rate": Decimal("12"), "minimum": Decimal("100")},
        ]
        result = simulate_payoff(debts, strategy="avalanche", extra_budget=Decimal("0"))
        self.assertGreater(result.total_interest, Decimal("0"))

    def test_debt_free_date_computed_from_start_date(self):
        debts = [
            {"id": 1, "name": "Kredit", "balance": Decimal("500"), "rate": Decimal("0"), "minimum": Decimal("500")},
        ]
        result = simulate_payoff(debts, strategy="avalanche", start_date=date(2026, 9, 3))
        self.assertEqual(result.months, 1)
        self.assertEqual(result.debt_free_date, date(2026, 10, 1))

    def test_reached_max_months_flag_when_payments_never_cover_balance(self):
        debts = [
            {"id": 1, "name": "Nie getilgt", "balance": Decimal("100000"), "rate": Decimal("30"), "minimum": Decimal("1")},
        ]
        result = simulate_payoff(debts, strategy="avalanche", max_months=6)
        self.assertTrue(result.reached_max)
        self.assertEqual(result.months, 6)


class DebtCategoryLinkTests(TestCase):
    """Jede Schuld bekommt automatisch einen eigenen, verknüpften Umschlag, über den
    sich Buchungen mit ihr verknüpfen lassen (statt einer separaten Zahlungstabelle)."""

    def test_creating_debt_auto_creates_linked_category(self):
        debt = Debt.objects.create(
            name="Kreditkarte", principal=Decimal("1000"), current_balance=Decimal("1000"),
            interest_rate=Decimal("10"), minimum_payment=Decimal("100"),
        )
        self.assertIsNotNone(debt.category)
        self.assertEqual(debt.category.name, "Kreditkarte")
        self.assertEqual(debt.category.kind, Category.Kind.DEBT)
        self.assertEqual(debt.category.monthly_budget, Decimal("100"))
        self.assertFalse(debt.category.is_archived)

    def test_renaming_debt_renames_linked_category(self):
        debt = Debt.objects.create(
            name="Alter Name", principal=Decimal("1000"), current_balance=Decimal("1000"),
            interest_rate=Decimal("0"), minimum_payment=Decimal("50"),
        )
        debt.name = "Neuer Name"
        debt.save()
        debt.category.refresh_from_db()
        self.assertEqual(debt.category.name, "Neuer Name")

    def test_editing_monthly_budget_after_creation_is_not_overwritten(self):
        """Vorbelegung nur bei Erstellung — danach bleibt das Budget frei änderbar."""
        debt = Debt.objects.create(
            name="Kredit", principal=Decimal("1000"), current_balance=Decimal("1000"),
            interest_rate=Decimal("0"), minimum_payment=Decimal("50"),
        )
        debt.category.monthly_budget = Decimal("999")
        debt.category.save()
        debt.minimum_payment = Decimal("75")
        debt.save()
        debt.category.refresh_from_db()
        self.assertEqual(debt.category.monthly_budget, Decimal("999"))

    def test_deleting_debt_archives_but_keeps_category(self):
        debt = Debt.objects.create(
            name="Kredit", principal=Decimal("1000"), current_balance=Decimal("1000"),
            interest_rate=Decimal("0"), minimum_payment=Decimal("50"),
        )
        category_id = debt.category_id
        debt.delete()
        category = Category.objects.get(pk=category_id)
        self.assertTrue(category.is_archived)

    def test_transaction_on_debt_category_reduces_balance(self):
        account = Account.objects.create(name="Girokonto", starting_balance=Decimal("0"))
        debt = Debt.objects.create(
            name="Kredit", principal=Decimal("1000"), current_balance=Decimal("1000"),
            interest_rate=Decimal("0"), minimum_payment=Decimal("50"),
        )
        Transaction.objects.create(
            account=account, category=debt.category, date=date(2026, 9, 5), amount=Decimal("-100"),
        )
        debt.refresh_from_db()
        self.assertEqual(debt.current_balance, Decimal("900"))
        self.assertFalse(debt.is_paid_off)

    def test_transaction_paying_off_debt_archives_category(self):
        account = Account.objects.create(name="Girokonto", starting_balance=Decimal("0"))
        debt = Debt.objects.create(
            name="Kredit", principal=Decimal("100"), current_balance=Decimal("100"),
            interest_rate=Decimal("0"), minimum_payment=Decimal("100"),
        )
        Transaction.objects.create(
            account=account, category=debt.category, date=date(2026, 9, 5), amount=Decimal("-100"),
        )
        debt.refresh_from_db()
        self.assertTrue(debt.is_paid_off)
        self.assertTrue(debt.category.is_archived)

    def test_deleting_transaction_reverses_balance(self):
        account = Account.objects.create(name="Girokonto", starting_balance=Decimal("0"))
        debt = Debt.objects.create(
            name="Kredit", principal=Decimal("1000"), current_balance=Decimal("1000"),
            interest_rate=Decimal("0"), minimum_payment=Decimal("50"),
        )
        txn = Transaction.objects.create(
            account=account, category=debt.category, date=date(2026, 9, 5), amount=Decimal("-100"),
        )
        txn.delete()
        debt.refresh_from_db()
        self.assertEqual(debt.current_balance, Decimal("1000"))


class DebtApiTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="tester", password="testpass12345")
        self.client.login(username="tester", password="testpass12345")
        self.account = Account.objects.create(name="Girokonto", starting_balance=Decimal("0"))

    def test_create_debt_and_record_payment_reduces_balance(self):
        response = self.client.post(
            "/api/debts/",
            {
                "name": "Kreditkarte",
                "principal": "1000",
                "current_balance": "1000",
                "interest_rate": "10",
                "minimum_payment": "100",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        debt_id = response.json()["id"]

        response = self.client.post(
            f"/api/debts/{debt_id}/payments/",
            {"account": self.account.id, "date": "2026-09-05", "amount": "100"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["debt"]["current_balance"], "900.00")
        self.assertEqual(Debt.objects.get(id=debt_id).current_balance, Decimal("900"))

        history = self.client.get(f"/api/debts/{debt_id}/payments/")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.json()), 1)
        self.assertEqual(history.json()[0]["amount"], "-100.00")

    def test_delete_debt(self):
        debt = Debt.objects.create(
            name="Kredit", principal=Decimal("100"), current_balance=Decimal("100"),
            interest_rate=Decimal("0"), minimum_payment=Decimal("10"),
        )
        response = self.client.delete(f"/api/debts/{debt.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Debt.objects.filter(id=debt.id).exists())


class PayoffApiTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="tester", password="testpass12345")
        self.client.login(username="tester", password="testpass12345")

    def test_payoff_endpoint_returns_schedule_for_open_debts(self):
        Debt.objects.create(
            name="Kredit", principal=Decimal("1000"), current_balance=Decimal("1000"),
            interest_rate=Decimal("10"), minimum_payment=Decimal("100"),
        )
        response = self.client.get("/api/debts/payoff/", {"strategy": "avalanche", "extra": "50"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["strategy"], "avalanche")
        self.assertGreater(len(data["schedule"]), 0)
        self.assertEqual(data["payoff_order"], ["Kredit"])

    def test_payoff_endpoint_rejects_anonymous_user(self):
        self.client.logout()
        response = self.client.get("/api/debts/payoff/")
        self.assertEqual(response.status_code, 403)
