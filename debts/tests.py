from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from core.models import Account, Category, Transaction

from .models import Debt
from .services import accrue_monthly_interest, simulate_payoff


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

    def test_editing_transaction_amount_rebalances_debt(self):
        account = Account.objects.create(name="Girokonto", starting_balance=Decimal("0"))
        debt = Debt.objects.create(
            name="Kredit", principal=Decimal("1000"), current_balance=Decimal("1000"),
            interest_rate=Decimal("0"), minimum_payment=Decimal("50"),
        )
        txn = Transaction.objects.create(
            account=account, category=debt.category, date=date(2026, 9, 5), amount=Decimal("-100"),
        )
        debt.refresh_from_db()
        self.assertEqual(debt.current_balance, Decimal("900"))

        txn.amount = Decimal("-150")
        txn.save()
        debt.refresh_from_db()
        self.assertEqual(debt.current_balance, Decimal("850"))

    def test_moving_transaction_off_debt_category_reverses_balance(self):
        account = Account.objects.create(name="Girokonto", starting_balance=Decimal("0"))
        other_category = Category.objects.create(name="Sonstiges", kind=Category.Kind.VARIABLE)
        debt = Debt.objects.create(
            name="Kredit", principal=Decimal("1000"), current_balance=Decimal("1000"),
            interest_rate=Decimal("0"), minimum_payment=Decimal("50"),
        )
        txn = Transaction.objects.create(
            account=account, category=debt.category, date=date(2026, 9, 5), amount=Decimal("-100"),
        )
        debt.refresh_from_db()
        self.assertEqual(debt.current_balance, Decimal("900"))

        txn.category = other_category
        txn.save()
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

    def test_edit_debt_via_api(self):
        debt = Debt.objects.create(
            name="Kredit", principal=Decimal("1000"), current_balance=Decimal("1000"),
            interest_rate=Decimal("10"), minimum_payment=Decimal("100"),
        )
        response = self.client.put(
            f"/api/debts/{debt.id}/",
            {
                "name": "Kredit umbenannt",
                "creditor": "Neue Bank",
                "principal": "1000",
                "current_balance": "800",
                "interest_rate": "8",
                "minimum_payment": "120",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        debt.refresh_from_db()
        self.assertEqual(debt.name, "Kredit umbenannt")
        self.assertEqual(debt.current_balance, Decimal("800"))
        self.assertEqual(debt.category.name, "Kredit umbenannt")


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


class DebtAccountLinkTests(TestCase):
    """Eine Schuld kann direkt mit einem Konto verknüpft werden (z.B. Kreditkarte) —
    dann verändert JEDE Buchung auf diesem Konto automatisch die Restschuld, nicht nur
    Buchungen auf dem dedizierten Umschlag (siehe DebtCategoryLinkTests oben)."""

    def setUp(self):
        self.card = Account.objects.create(name="Kreditkarte", account_type=Account.AccountType.CREDIT)
        self.debt = Debt.objects.create(
            name="Kreditkarte", principal=Decimal("500"), current_balance=Decimal("500"),
            interest_rate=Decimal("18"), minimum_payment=Decimal("50"), account=self.card,
        )

    def test_purchase_on_linked_account_increases_balance(self):
        category = Category.objects.create(name="Lebensmittel", kind=Category.Kind.VARIABLE)
        Transaction.objects.create(
            account=self.card, category=category, date=date(2026, 9, 5), amount=Decimal("-80"),
        )
        self.debt.refresh_from_db()
        self.assertEqual(self.debt.current_balance, Decimal("580"))

    def test_credit_to_linked_account_decreases_balance(self):
        Transaction.objects.create(account=self.card, date=date(2026, 9, 5), amount=Decimal("200"))
        self.debt.refresh_from_db()
        self.assertEqual(self.debt.current_balance, Decimal("300"))

    def test_transaction_on_linked_account_and_its_own_category_counts_once(self):
        Transaction.objects.create(
            account=self.card, category=self.debt.category, date=date(2026, 9, 5), amount=Decimal("-50"),
        )
        self.debt.refresh_from_db()
        # Nur der Konto-Weg zählt (Delta +50), nicht zusätzlich der Umschlag-Weg (Delta -50).
        self.assertEqual(self.debt.current_balance, Decimal("550"))

    def test_editing_amount_on_linked_account_rebalances_debt(self):
        txn = Transaction.objects.create(account=self.card, date=date(2026, 9, 5), amount=Decimal("-80"))
        self.debt.refresh_from_db()
        self.assertEqual(self.debt.current_balance, Decimal("580"))
        txn.amount = Decimal("-120")
        txn.save()
        self.debt.refresh_from_db()
        self.assertEqual(self.debt.current_balance, Decimal("620"))

    def test_deleting_transaction_on_linked_account_reverses_balance(self):
        txn = Transaction.objects.create(account=self.card, date=date(2026, 9, 5), amount=Decimal("-80"))
        txn.delete()
        self.debt.refresh_from_db()
        self.assertEqual(self.debt.current_balance, Decimal("500"))

    def test_transfer_to_linked_card_account_reduces_debt(self):
        checking = Account.objects.create(name="Girokonto", starting_balance=Decimal("1000"))
        User.objects.create_user(username="tester", password="testpass12345")
        self.client.login(username="tester", password="testpass12345")
        response = self.client.post(
            "/api/transfers/",
            {"from_account": checking.id, "to_account": self.card.id, "amount": "200", "date": "2026-09-05"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.debt.refresh_from_db()
        self.assertEqual(self.debt.current_balance, Decimal("300"))


class DebtInterestAccrualTests(TestCase):
    """Der Zinssatz einer Schuld wird jetzt auch echt (nicht nur simuliert) einmal
    pro Kalendermonat auf current_balance verbucht."""

    def test_classic_debt_interest_directly_increases_balance(self):
        debt = Debt.objects.create(
            name="Privatdarlehen", principal=Decimal("1000"), current_balance=Decimal("1000"),
            interest_rate=Decimal("12"), minimum_payment=Decimal("50"),
        )
        accrued = accrue_monthly_interest(today=date(2026, 9, 15))
        debt.refresh_from_db()
        self.assertEqual(len(accrued), 1)
        self.assertEqual(debt.current_balance, Decimal("1010.00"))
        self.assertEqual(debt.last_interest_year, 2026)
        self.assertEqual(debt.last_interest_month, 9)

    def test_classic_debt_interest_not_double_applied_same_month(self):
        debt = Debt.objects.create(
            name="Privatdarlehen", principal=Decimal("1000"), current_balance=Decimal("1000"),
            interest_rate=Decimal("12"), minimum_payment=Decimal("50"),
        )
        accrue_monthly_interest(today=date(2026, 9, 5))
        accrue_monthly_interest(today=date(2026, 9, 25))
        debt.refresh_from_db()
        self.assertEqual(debt.current_balance, Decimal("1010.00"))

    def test_classic_debt_interest_accrues_again_next_month(self):
        debt = Debt.objects.create(
            name="Privatdarlehen", principal=Decimal("1000"), current_balance=Decimal("1000"),
            interest_rate=Decimal("12"), minimum_payment=Decimal("50"),
        )
        accrue_monthly_interest(today=date(2026, 9, 5))
        accrue_monthly_interest(today=date(2026, 10, 5))
        debt.refresh_from_db()
        self.assertEqual(debt.current_balance, Decimal("1020.10"))

    def test_account_linked_debt_interest_posts_real_transaction(self):
        card = Account.objects.create(name="Kreditkarte", account_type=Account.AccountType.CREDIT)
        debt = Debt.objects.create(
            name="Kreditkarte", principal=Decimal("500"), current_balance=Decimal("500"),
            interest_rate=Decimal("24"), minimum_payment=Decimal("50"), account=card,
        )
        accrue_monthly_interest(today=date(2026, 9, 15))
        debt.refresh_from_db()
        self.assertEqual(debt.current_balance, Decimal("510.00"))
        txn = Transaction.objects.get(account=card)
        self.assertEqual(txn.amount, Decimal("-10.00"))
        self.assertEqual(txn.import_ref, f"debt-interest-{debt.id}-2026-09")

    def test_account_linked_debt_interest_not_double_applied_same_month(self):
        card = Account.objects.create(name="Kreditkarte", account_type=Account.AccountType.CREDIT)
        debt = Debt.objects.create(
            name="Kreditkarte", principal=Decimal("500"), current_balance=Decimal("500"),
            interest_rate=Decimal("24"), minimum_payment=Decimal("50"), account=card,
        )
        accrue_monthly_interest(today=date(2026, 9, 5))
        accrue_monthly_interest(today=date(2026, 9, 25))
        debt.refresh_from_db()
        self.assertEqual(debt.current_balance, Decimal("510.00"))
        self.assertEqual(Transaction.objects.filter(account=card).count(), 1)

    def test_account_linked_debt_reaccrues_if_interest_transaction_deleted(self):
        card = Account.objects.create(name="Kreditkarte", account_type=Account.AccountType.CREDIT)
        debt = Debt.objects.create(
            name="Kreditkarte", principal=Decimal("500"), current_balance=Decimal("500"),
            interest_rate=Decimal("24"), minimum_payment=Decimal("50"), account=card,
        )
        accrue_monthly_interest(today=date(2026, 9, 5))
        for txn in Transaction.objects.filter(account=card):
            txn.delete()
        debt.refresh_from_db()
        self.assertEqual(debt.current_balance, Decimal("500"))
        accrue_monthly_interest(today=date(2026, 9, 25))
        debt.refresh_from_db()
        self.assertEqual(debt.current_balance, Decimal("510.00"))

    def test_zero_interest_rate_does_not_create_noise(self):
        debt = Debt.objects.create(
            name="Zinslos", principal=Decimal("1000"), current_balance=Decimal("1000"),
            interest_rate=Decimal("0"), minimum_payment=Decimal("50"),
        )
        accrued = accrue_monthly_interest(today=date(2026, 9, 5))
        debt.refresh_from_db()
        self.assertEqual(accrued, [])
        self.assertEqual(debt.current_balance, Decimal("1000"))

    def test_paid_off_debt_is_skipped(self):
        Debt.objects.create(
            name="Getilgt", principal=Decimal("1000"), current_balance=Decimal("0"),
            interest_rate=Decimal("10"), minimum_payment=Decimal("50"), is_paid_off=True,
        )
        accrued = accrue_monthly_interest(today=date(2026, 9, 5))
        self.assertEqual(accrued, [])


class DebtAccountLinkApiTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="tester", password="testpass12345")
        self.client.login(username="tester", password="testpass12345")
        self.card = Account.objects.create(name="Kreditkarte", account_type=Account.AccountType.CREDIT)
        self.checking = Account.objects.create(name="Girokonto", starting_balance=Decimal("1000"))

    def test_create_debt_with_linked_account_via_api(self):
        response = self.client.post(
            "/api/debts/",
            {
                "name": "Kreditkarte", "principal": "500", "current_balance": "500",
                "interest_rate": "18", "minimum_payment": "50", "account": self.card.id,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["account"], self.card.id)
        self.assertEqual(response.json()["account_name"], "Kreditkarte")

    def test_account_can_only_be_linked_to_one_debt(self):
        Debt.objects.create(
            name="Erste", principal=Decimal("100"), current_balance=Decimal("100"),
            interest_rate=Decimal("0"), minimum_payment=Decimal("10"), account=self.card,
        )
        response = self.client.post(
            "/api/debts/",
            {
                "name": "Zweite", "principal": "100", "current_balance": "100",
                "interest_rate": "0", "minimum_payment": "10", "account": self.card.id,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_manual_payment_endpoint_rejected_for_account_linked_debt(self):
        debt = Debt.objects.create(
            name="Kreditkarte", principal=Decimal("500"), current_balance=Decimal("500"),
            interest_rate=Decimal("0"), minimum_payment=Decimal("50"), account=self.card,
        )
        response = self.client.post(
            f"/api/debts/{debt.id}/payments/",
            {"account": self.checking.id, "date": "2026-09-05", "amount": "100"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_payments_history_returns_linked_account_transactions(self):
        debt = Debt.objects.create(
            name="Kreditkarte", principal=Decimal("500"), current_balance=Decimal("500"),
            interest_rate=Decimal("0"), minimum_payment=Decimal("50"), account=self.card,
        )
        Transaction.objects.create(account=self.card, date=date(2026, 9, 5), amount=Decimal("-40"))
        response = self.client.get(f"/api/debts/{debt.id}/payments/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_dashboard_accrues_interest_automatically(self):
        debt = Debt.objects.create(
            name="Kreditkarte", principal=Decimal("500"), current_balance=Decimal("500"),
            interest_rate=Decimal("24"), minimum_payment=Decimal("50"), account=self.card,
        )
        response = self.client.get("/api/dashboard/")
        self.assertEqual(response.status_code, 200)
        debt.refresh_from_db()
        self.assertEqual(debt.current_balance, Decimal("510.00"))
