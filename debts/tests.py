from datetime import date
from decimal import Decimal

from django.test import TestCase

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
