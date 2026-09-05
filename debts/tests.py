from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from core.models import Account, Category, Transaction

from .models import Debt
from .services import (
    accrue_monthly_interest,
    allocate_extra_once,
    check_new_milestones,
    eligible_envelope_surplus,
    emergency_fund_status,
    simulate_payoff,
    sweep_window_status,
)


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

    def test_max_extra_zero_blocks_any_extra_payment(self):
        """Ein Ratenkredit mit fixem Tilgungsplan (max_extra=0) darf trotz Priorität
        keine Zuzahlung erhalten — die einzige Schuld im Plan, also bleibt das gesamte
        Extra-Budget ungenutzt."""
        debts = [
            {
                "id": 1, "name": "Fixer Ratenkredit", "balance": Decimal("2000"), "rate": Decimal("5"),
                "minimum": Decimal("100"), "max_extra": Decimal("0"),
            },
        ]
        result = simulate_payoff(debts, strategy="avalanche", extra_budget=Decimal("300"))
        without_extra = simulate_payoff(
            [{"id": 1, "name": "Fixer Ratenkredit", "balance": Decimal("2000"), "rate": Decimal("5"), "minimum": Decimal("100")}],
            strategy="avalanche", extra_budget=Decimal("0"),
        )
        self.assertEqual(result.months, without_extra.months)
        self.assertGreater(result.unallocated_extra, Decimal("0"))

    def test_capped_debt_overflow_rolls_to_next_priority_debt(self):
        """Was ein gedeckelter Kredit nicht aufnehmen kann, fliesst an die nächste
        Schuld in der Prioritätsreihenfolge, statt zu verfallen. Zins bewusst 0 und auf
        einen Monat begrenzt, damit die Beträge exakt nachrechenbar bleiben — es geht
        hier nur um die Verteilung innerhalb eines Monats, nicht um den Gesamtverlauf."""
        debts = [
            {
                "id": 1, "name": "Gedeckelt", "balance": Decimal("1000"), "rate": Decimal("0"),
                "minimum": Decimal("50"), "max_extra": Decimal("20"),
            },
            {"id": 2, "name": "Frei", "balance": Decimal("1000"), "rate": Decimal("0"), "minimum": Decimal("50")},
        ]
        result = simulate_payoff(debts, strategy="avalanche", extra_budget=Decimal("200"), max_months=1)
        # Beide Schulden sind noch weit offen, das Extra-Budget passt komplett rein —
        # nichts bleibt unplatziert.
        self.assertEqual(result.unallocated_extra, Decimal("0"))
        first_month = result.schedule[0]
        # Gedeckelter Kredit bekommt nur seine erlaubten 20 Extra (1000 - 50 - 20 = 930),
        # der Rest (180) fliesst an den ungedeckelten (1000 - 50 - 180 = 770).
        self.assertEqual(first_month["balances"][1], Decimal("930"))
        self.assertEqual(first_month["balances"][2], Decimal("770"))

    def test_unallocated_extra_grows_once_only_capped_debt_remains(self):
        """Sobald die ungedeckelte Schuld getilgt ist und nur noch eine stark gedeckelte
        übrig bleibt, kann das Extra-Budget nicht mehr vollständig verteilt werden — das
        muss sich in unallocated_extra zeigen, nicht stillschweigend verschwinden."""
        debts = [
            {
                "id": 1, "name": "Nur gedeckelt", "balance": Decimal("500"), "rate": Decimal("0"),
                "minimum": Decimal("50"), "max_extra": Decimal("20"),
            },
        ]
        result = simulate_payoff(debts, strategy="avalanche", extra_budget=Decimal("200"))
        self.assertGreater(result.unallocated_extra, Decimal("0"))

    def test_max_extra_none_behaves_as_unlimited(self):
        debts_with_key = [
            {"id": 1, "name": "Kreditkarte", "balance": Decimal("3000"), "rate": Decimal("10"), "minimum": Decimal("100"), "max_extra": None},
        ]
        debts_without_key = [
            {"id": 1, "name": "Kreditkarte", "balance": Decimal("3000"), "rate": Decimal("10"), "minimum": Decimal("100")},
        ]
        with_key = simulate_payoff(debts_with_key, strategy="avalanche", extra_budget=Decimal("300"))
        without_key = simulate_payoff(debts_without_key, strategy="avalanche", extra_budget=Decimal("300"))
        self.assertEqual(with_key.months, without_key.months)
        self.assertEqual(with_key.unallocated_extra, Decimal("0"))
        self.assertEqual(without_key.unallocated_extra, Decimal("0"))


class AllocateExtraOnceTests(TestCase):
    """Einmalige Verteilung eines Extra-Betrags auf offene Schulden — Grundlage
    für den Monatsende-Sweep-Vorschlag: die App löst keine echte Überweisung
    aus, sondern zeigt nur, wie sich ein Betrag nach Priorität verteilen würde."""

    def test_no_extra_budget_returns_no_allocations(self):
        debts = [{"id": 1, "name": "Kredit", "balance": Decimal("1000"), "rate": Decimal("5")}]
        result = allocate_extra_once(debts, strategy="avalanche", extra_budget=Decimal("0"))
        self.assertEqual(result.allocations, [])
        self.assertEqual(result.unallocated, Decimal("0"))

    def test_no_open_debts_reports_everything_unallocated(self):
        result = allocate_extra_once([], strategy="avalanche", extra_budget=Decimal("100"))
        self.assertEqual(result.allocations, [])
        self.assertEqual(result.unallocated, Decimal("100"))

    def test_avalanche_prioritizes_highest_rate(self):
        debts = [
            {"id": 1, "name": "Niedrigzins", "balance": Decimal("1000"), "rate": Decimal("2")},
            {"id": 2, "name": "Hochzins", "balance": Decimal("1000"), "rate": Decimal("20")},
        ]
        result = allocate_extra_once(debts, strategy="avalanche", extra_budget=Decimal("100"))
        self.assertEqual(result.allocations, [{"id": 2, "name": "Hochzins", "amount": Decimal("100")}])
        self.assertEqual(result.unallocated, Decimal("0"))

    def test_snowball_prioritizes_smallest_balance(self):
        debts = [
            {"id": 1, "name": "Kleine Schuld", "balance": Decimal("300"), "rate": Decimal("2")},
            {"id": 2, "name": "Grosse Schuld", "balance": Decimal("5000"), "rate": Decimal("20")},
        ]
        result = allocate_extra_once(debts, strategy="snowball", extra_budget=Decimal("100"))
        self.assertEqual(result.allocations, [{"id": 1, "name": "Kleine Schuld", "amount": Decimal("100")}])

    def test_capped_debt_overflow_rolls_to_next_priority_debt(self):
        debts = [
            {"id": 1, "name": "Gedeckelt", "balance": Decimal("1000"), "rate": Decimal("20"), "max_extra": Decimal("20")},
            {"id": 2, "name": "Frei", "balance": Decimal("1000"), "rate": Decimal("2")},
        ]
        result = allocate_extra_once(debts, strategy="avalanche", extra_budget=Decimal("100"))
        self.assertEqual(
            result.allocations,
            [{"id": 1, "name": "Gedeckelt", "amount": Decimal("20")}, {"id": 2, "name": "Frei", "amount": Decimal("80")}],
        )
        self.assertEqual(result.unallocated, Decimal("0"))

    def test_max_extra_zero_excludes_debt_entirely(self):
        debts = [
            {"id": 1, "name": "Fixer Ratenkredit", "balance": Decimal("1000"), "rate": Decimal("20"), "max_extra": Decimal("0")},
            {"id": 2, "name": "Frei", "balance": Decimal("1000"), "rate": Decimal("2")},
        ]
        result = allocate_extra_once(debts, strategy="avalanche", extra_budget=Decimal("100"))
        self.assertEqual(result.allocations, [{"id": 2, "name": "Frei", "amount": Decimal("100")}])
        self.assertEqual(result.unallocated, Decimal("0"))

    def test_surplus_beyond_total_debt_is_unallocated_without_flag(self):
        """Mehr Extra-Budget als insgesamt Schulden bestehen ist kein Kappungsproblem,
        sondern schlicht kein Bedarf mehr — bleibt trotzdem korrekt unallocated."""
        debts = [{"id": 1, "name": "Kleiner Rest", "balance": Decimal("50"), "rate": Decimal("5")}]
        result = allocate_extra_once(debts, strategy="avalanche", extra_budget=Decimal("200"))
        self.assertEqual(result.allocations, [{"id": 1, "name": "Kleiner Rest", "amount": Decimal("50")}])
        self.assertEqual(result.unallocated, Decimal("150"))


class EligibleEnvelopeSurplusTests(TestCase):
    """Nutzt das echte heutige Datum statt eines fixen Jahres/Monats, da
    Category.created_at (auto_now_add) nicht auf ein Testdatum kontrollierbar ist."""

    def test_positive_rollover_of_ordinary_envelope_counts(self):
        today = date.today()
        category = Category.objects.create(name="Lebensmittel", kind=Category.Kind.VARIABLE, monthly_budget=Decimal("400"))
        account = Account.objects.create(name="Girokonto", starting_balance=Decimal("0"))
        Transaction.objects.create(account=account, category=category, date=today, amount=Decimal("-350"))
        total, sources = eligible_envelope_surplus(today.year, today.month)
        self.assertEqual(total, Decimal("50"))
        self.assertEqual(sources, [{"id": category.id, "name": "Lebensmittel", "amount": Decimal("50")}])

    def test_overspent_envelope_does_not_reduce_total(self):
        today = date.today()
        account = Account.objects.create(name="Girokonto", starting_balance=Decimal("0"))
        overspent = Category.objects.create(name="Auto", kind=Category.Kind.VARIABLE, monthly_budget=Decimal("100"))
        Transaction.objects.create(account=account, category=overspent, date=today, amount=Decimal("-250"))
        total, sources = eligible_envelope_surplus(today.year, today.month)
        self.assertEqual(total, Decimal("0"))
        self.assertEqual(sources, [])

    def test_savings_goal_envelope_excluded(self):
        today = date.today()
        Category.objects.create(
            name="Ferien", kind=Category.Kind.SAVINGS, monthly_budget=Decimal("200"), target_amount=Decimal("2000"),
        )
        total, sources = eligible_envelope_surplus(today.year, today.month)
        self.assertEqual(total, Decimal("0"))
        self.assertEqual(sources, [])

    def test_debt_and_income_categories_excluded(self):
        today = date.today()
        Debt.objects.create(
            name="Kredit", principal=Decimal("1000"), current_balance=Decimal("1000"),
            interest_rate=Decimal("0"), minimum_payment=Decimal("50"),
        )
        Category.objects.create(name="Lohn", kind=Category.Kind.INCOME, monthly_budget=Decimal("5000"))
        total, sources = eligible_envelope_surplus(today.year, today.month)
        self.assertEqual(total, Decimal("0"))
        self.assertEqual(sources, [])


class EmergencyFundStatusTests(TestCase):
    """Notfallfonds-Priorität: bewährtes Prinzip aus der Schuldenberatung — erst
    einen Puffer aufbauen, bevor Extra-Budget aggressiv auf Schulden verteilt wird."""

    def test_no_emergency_fund_marked_returns_zero_gap(self):
        Category.objects.create(name="Ferien", kind=Category.Kind.SAVINGS, target_amount=Decimal("2000"))
        today = date.today()
        fund, target, current, gap = emergency_fund_status(today.year, today.month)
        self.assertIsNone(fund)
        self.assertEqual(gap, Decimal("0"))

    def test_marked_fund_without_target_amount_treated_as_none(self):
        Category.objects.create(name="Notgroschen", kind=Category.Kind.SAVINGS, is_emergency_fund=True)
        today = date.today()
        fund, target, current, gap = emergency_fund_status(today.year, today.month)
        self.assertIsNone(fund)
        self.assertEqual(gap, Decimal("0"))

    def test_computes_gap_to_target(self):
        today = date.today()
        category = Category.objects.create(
            name="Notgroschen", kind=Category.Kind.SAVINGS, monthly_budget=Decimal("100"),
            target_amount=Decimal("3000"), is_emergency_fund=True,
        )
        account = Account.objects.create(name="Girokonto", starting_balance=Decimal("0"))
        Transaction.objects.create(account=account, category=category, date=today, amount=Decimal("-40"))
        fund, target, current, gap = emergency_fund_status(today.year, today.month)
        self.assertEqual(fund, category)
        self.assertEqual(target, Decimal("3000"))
        self.assertEqual(current, Decimal("60"))
        self.assertEqual(gap, Decimal("2940"))

    def test_gap_is_zero_once_fund_reaches_target(self):
        today = date.today()
        category = Category.objects.create(
            name="Notgroschen", kind=Category.Kind.SAVINGS, monthly_budget=Decimal("5000"),
            target_amount=Decimal("3000"), is_emergency_fund=True,
        )
        _, _, _, gap = emergency_fund_status(today.year, today.month)
        self.assertEqual(gap, Decimal("0"))

    def test_archived_emergency_fund_ignored(self):
        Category.objects.create(
            name="Notgroschen", kind=Category.Kind.SAVINGS, target_amount=Decimal("3000"),
            is_emergency_fund=True, is_archived=True,
        )
        today = date.today()
        fund, _, _, gap = emergency_fund_status(today.year, today.month)
        self.assertIsNone(fund)
        self.assertEqual(gap, Decimal("0"))


class SimulatePayoffEmergencyFundTests(TestCase):
    def test_extra_budget_fills_gap_before_any_debt(self):
        debts = [{"id": 1, "name": "Kredit", "balance": Decimal("1000"), "rate": Decimal("0"), "minimum": Decimal("50")}]
        result = simulate_payoff(
            debts, strategy="avalanche", extra_budget=Decimal("100"), emergency_fund_gap=Decimal("250"),
        )
        first_month = result.schedule[0]
        # 100 Extra-Budget geht komplett in den Notfallfonds, die Schuld bekommt in
        # Monat 1 nur ihre Mindestrate (1000 - 50 = 950), keine Zuzahlung.
        self.assertEqual(first_month["balances"][1], Decimal("950"))
        self.assertEqual(result.emergency_fund_total, Decimal("250"))

    def test_extra_flows_to_debt_once_gap_filled(self):
        debts = [{"id": 1, "name": "Kredit", "balance": Decimal("1000"), "rate": Decimal("0"), "minimum": Decimal("50")}]
        result = simulate_payoff(
            debts, strategy="avalanche", extra_budget=Decimal("100"), emergency_fund_gap=Decimal("150"),
            start_date=date(2026, 9, 1),
        )
        # Monat 1: 100 in den Fonds (Lücke 150 -> 50 verbleibend), Schuld nur Mindestrate.
        self.assertEqual(result.schedule[0]["balances"][1], Decimal("950"))
        # Monat 2: 50 schliessen den Fonds, restliche 50 Extra-Budget gehen an die Schuld.
        self.assertEqual(result.schedule[1]["balances"][1], Decimal("850"))
        self.assertEqual(result.emergency_fund_total, Decimal("150"))
        # Der Fonds wird während der Verarbeitung von Monat 2 (Datum 2026-11-01 in
        # der Simulation, siehe schedule[1]["date"]) geschlossen.
        self.assertEqual(result.emergency_fund_filled_date, date(2026, 11, 1))

    def test_zero_gap_behaves_exactly_as_before(self):
        debts = [{"id": 1, "name": "Kredit", "balance": Decimal("1000"), "rate": Decimal("5"), "minimum": Decimal("100")}]
        without_param = simulate_payoff(debts, strategy="avalanche", extra_budget=Decimal("50"))
        with_zero_gap = simulate_payoff(
            debts, strategy="avalanche", extra_budget=Decimal("50"), emergency_fund_gap=Decimal("0")
        )
        self.assertEqual(without_param.months, with_zero_gap.months)
        self.assertEqual(without_param.total_interest, with_zero_gap.total_interest)


class AllocateExtraOnceEmergencyFundTests(TestCase):
    def test_gap_consumes_pool_before_debts(self):
        debts = [{"id": 1, "name": "Kredit", "balance": Decimal("1000"), "rate": Decimal("10")}]
        result = allocate_extra_once(
            debts, strategy="avalanche", extra_budget=Decimal("100"), emergency_fund_gap=Decimal("60")
        )
        self.assertEqual(result.to_emergency_fund, Decimal("60"))
        self.assertEqual(result.allocations, [{"id": 1, "name": "Kredit", "amount": Decimal("40")}])

    def test_gap_larger_than_pool_leaves_nothing_for_debts(self):
        debts = [{"id": 1, "name": "Kredit", "balance": Decimal("1000"), "rate": Decimal("10")}]
        result = allocate_extra_once(
            debts, strategy="avalanche", extra_budget=Decimal("100"), emergency_fund_gap=Decimal("500")
        )
        self.assertEqual(result.to_emergency_fund, Decimal("100"))
        self.assertEqual(result.allocations, [])
        self.assertEqual(result.unallocated, Decimal("0"))

    def test_zero_gap_behaves_exactly_as_before(self):
        debts = [{"id": 1, "name": "Kredit", "balance": Decimal("1000"), "rate": Decimal("10")}]
        without_param = allocate_extra_once(debts, strategy="avalanche", extra_budget=Decimal("100"))
        with_zero_gap = allocate_extra_once(
            debts, strategy="avalanche", extra_budget=Decimal("100"), emergency_fund_gap=Decimal("0")
        )
        self.assertEqual(without_param.allocations, with_zero_gap.allocations)
        self.assertEqual(with_zero_gap.to_emergency_fund, Decimal("0"))


class SweepWindowStatusTests(TestCase):
    """Der Sweep-Vorschlag darf nicht mitten im Monat auftauchen: ein Umschlag-
    Übertrag wächst im Lauf des Monats einfach an, weil noch nicht alles
    ausgegeben wurde — das ist am 5. Tag kein "Überschuss", sondern Geld, das
    diesen Monat noch gebraucht wird. Sinnvoll ist der Vorschlag nur in den
    letzten SWEEP_WINDOW_DAYS Tagen des Budget-Monats."""

    def test_last_day_of_month_is_in_window(self):
        year, month, days_remaining, in_window = sweep_window_status(date(2026, 9, 30), 1)
        self.assertEqual((year, month), (2026, 9))
        self.assertEqual(days_remaining, 0)
        self.assertTrue(in_window)

    def test_exactly_five_days_remaining_is_in_window(self):
        _, _, days_remaining, in_window = sweep_window_status(date(2026, 9, 25), 1)
        self.assertEqual(days_remaining, 5)
        self.assertTrue(in_window)

    def test_six_days_remaining_is_not_in_window(self):
        _, _, days_remaining, in_window = sweep_window_status(date(2026, 9, 24), 1)
        self.assertEqual(days_remaining, 6)
        self.assertFalse(in_window)

    def test_respects_custom_month_start_day(self):
        """Budget-Monat läuft hier vom 25. bis zum 24. des Folgemonats — das
        Zeitfenster muss sich am tatsächlichen Periodenende orientieren, nicht
        am Ende des Kalendermonats."""
        year, month, days_remaining, in_window = sweep_window_status(date(2026, 9, 20), 25)
        self.assertEqual((year, month), (2026, 8))
        self.assertEqual(days_remaining, 4)
        self.assertTrue(in_window)


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

    def test_payoff_endpoint_reports_emergency_fund_status(self):
        today = date.today()
        fund = Category.objects.create(
            name="Notgroschen", kind=Category.Kind.SAVINGS, target_amount=Decimal("500"), is_emergency_fund=True,
        )
        Debt.objects.create(
            name="Kredit", principal=Decimal("1000"), current_balance=Decimal("1000"),
            interest_rate=Decimal("0"), minimum_payment=Decimal("100"),
        )
        response = self.client.get("/api/debts/payoff/", {"strategy": "avalanche", "extra": "100"})
        data = response.json()
        self.assertEqual(data["emergency_fund"]["category_id"], fund.id)
        self.assertEqual(data["emergency_fund"]["gap"], "500.00")
        # Das ganze Extra-Budget von Monat 1 geht zuerst in den Fonds — die Schuld
        # bekommt in month[0] nur ihre Mindestrate (1000-100=900).
        self.assertEqual(data["schedule"][0]["total_balance"], "900.00")

    def test_payoff_endpoint_without_emergency_fund_unaffected(self):
        Debt.objects.create(
            name="Kredit", principal=Decimal("1000"), current_balance=Decimal("1000"),
            interest_rate=Decimal("0"), minimum_payment=Decimal("100"),
        )
        response = self.client.get("/api/debts/payoff/", {"strategy": "avalanche", "extra": "100"})
        data = response.json()
        self.assertIsNone(data["emergency_fund"]["category_id"])
        self.assertEqual(data["emergency_fund"]["gap"], "0.00")
        self.assertEqual(data["schedule"][0]["total_balance"], "800.00")


class SweepProposalApiTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="tester", password="testpass12345")
        self.client.login(username="tester", password="testpass12345")

    def test_sweep_proposal_distributes_envelope_surplus_to_highest_priority_debt(self):
        today = date.today()
        category = Category.objects.create(name="Lebensmittel", kind=Category.Kind.VARIABLE, monthly_budget=Decimal("400"))
        account = Account.objects.create(name="Girokonto", starting_balance=Decimal("0"))
        Transaction.objects.create(account=account, category=category, date=today, amount=Decimal("-350"))
        Debt.objects.create(
            name="Kredit", principal=Decimal("1000"), current_balance=Decimal("1000"),
            interest_rate=Decimal("10"), minimum_payment=Decimal("100"),
        )
        response = self.client.get("/api/debts/sweep-proposal/", {"strategy": "avalanche"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_available"], "50.00")
        self.assertEqual(data["sources"], [{"id": category.id, "name": "Lebensmittel", "amount": "50.00"}])
        self.assertEqual(data["allocations"], [{"id": 1, "name": "Kredit", "amount": "50.00"}])
        self.assertEqual(data["unallocated"], "0.00")

    def test_sweep_proposal_with_no_surplus_returns_empty(self):
        Debt.objects.create(
            name="Kredit", principal=Decimal("1000"), current_balance=Decimal("1000"),
            interest_rate=Decimal("10"), minimum_payment=Decimal("100"),
        )
        response = self.client.get("/api/debts/sweep-proposal/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_available"], "0.00")
        self.assertEqual(data["allocations"], [])

    def test_sweep_proposal_reports_window_status_matching_service(self):
        from core.budget_month import get_month_start_day

        response = self.client.get("/api/debts/sweep-proposal/")
        data = response.json()
        _, _, expected_days, expected_in_window = sweep_window_status(date.today(), get_month_start_day())
        self.assertEqual(data["days_remaining"], expected_days)
        self.assertEqual(data["in_window"], expected_in_window)

    def test_sweep_proposal_diverts_to_emergency_fund_before_debts(self):
        today = date.today()
        fund = Category.objects.create(
            name="Notgroschen", kind=Category.Kind.SAVINGS, target_amount=Decimal("1000"), is_emergency_fund=True,
        )
        surplus_category = Category.objects.create(
            name="Lebensmittel", kind=Category.Kind.VARIABLE, monthly_budget=Decimal("400"),
        )
        account = Account.objects.create(name="Girokonto", starting_balance=Decimal("0"))
        Transaction.objects.create(account=account, category=surplus_category, date=today, amount=Decimal("-350"))
        Debt.objects.create(
            name="Kredit", principal=Decimal("1000"), current_balance=Decimal("1000"),
            interest_rate=Decimal("10"), minimum_payment=Decimal("100"),
        )
        response = self.client.get("/api/debts/sweep-proposal/")
        data = response.json()
        self.assertEqual(data["total_available"], "50.00")
        self.assertEqual(data["to_emergency_fund"], {"category_id": fund.id, "category_name": "Notgroschen", "amount": "50.00"})
        self.assertEqual(data["allocations"], [])

    def test_sweep_proposal_rejects_anonymous_user(self):
        self.client.logout()
        response = self.client.get("/api/debts/sweep-proposal/")
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


class CheckNewMilestonesTests(TestCase):
    """Meilenstein-Meldungen sind zustandsbehaftet (Debt.last_milestone_reached),
    damit dieselbe Meldung nicht bei jedem Dashboard-Aufruf erneut erscheint."""

    def test_no_milestone_below_25_percent(self):
        Debt.objects.create(
            name="Kredit", principal=Decimal("1000"), current_balance=Decimal("900"),
            interest_rate=Decimal("0"), minimum_payment=Decimal("50"),
        )
        self.assertEqual(check_new_milestones(), [])

    def test_25_percent_reported_once(self):
        debt = Debt.objects.create(
            name="Kredit", principal=Decimal("1000"), current_balance=Decimal("750"),
            interest_rate=Decimal("0"), minimum_payment=Decimal("50"),
        )
        self.assertEqual(check_new_milestones(), [{"debt_id": debt.id, "debt_name": "Kredit", "milestone": 25}])
        self.assertEqual(check_new_milestones(), [])
        debt.refresh_from_db()
        self.assertEqual(debt.last_milestone_reached, 25)

    def test_progressing_further_reports_next_milestone_only(self):
        debt = Debt.objects.create(
            name="Kredit", principal=Decimal("1000"), current_balance=Decimal("750"),
            interest_rate=Decimal("0"), minimum_payment=Decimal("50"),
        )
        check_new_milestones()
        debt.current_balance = Decimal("500")
        debt.save()
        self.assertEqual(check_new_milestones(), [{"debt_id": debt.id, "debt_name": "Kredit", "milestone": 50}])

    def test_fully_paid_off_debt_still_reports_100_percent_milestone(self):
        """Eine vollständig getilgte Schuld wird beim Auslösen automatisch
        is_paid_off=True gesetzt — der 100%-Meilenstein, der emotional der wichtigste
        ist, darf dadurch nicht verloren gehen."""
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
        self.assertEqual(check_new_milestones(), [{"debt_id": debt.id, "debt_name": "Kredit", "milestone": 100}])

    def test_multiple_debts_each_reported_independently(self):
        debt1 = Debt.objects.create(
            name="Erste", principal=Decimal("1000"), current_balance=Decimal("700"),
            interest_rate=Decimal("0"), minimum_payment=Decimal("50"),
        )
        debt2 = Debt.objects.create(
            name="Zweite", principal=Decimal("1000"), current_balance=Decimal("100"),
            interest_rate=Decimal("0"), minimum_payment=Decimal("50"),
        )
        result = check_new_milestones()
        self.assertEqual(
            {(r["debt_id"], r["milestone"]) for r in result},
            {(debt1.id, 25), (debt2.id, 75)},
        )


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
