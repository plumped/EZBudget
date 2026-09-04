import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand

from core.models import Account, Category, RecurringTransaction, Transaction
from debts.models import Debt


class Command(BaseCommand):
    help = "Legt Demo-Daten für ezbudget an (Konten, Umschläge, Buchungen, Schulden, Daueraufträge)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Vorher alle Daten löschen")

    def handle(self, *args, **options):
        if options["reset"]:
            RecurringTransaction.objects.all().delete()
            Transaction.objects.all().delete()
            Debt.objects.all().delete()
            Category.objects.all().delete()
            Account.objects.all().delete()
            self.stdout.write("Bestehende Daten gelöscht.")

        checking, _ = Account.objects.get_or_create(
            name="Girokonto",
            defaults=dict(account_type=Account.AccountType.CHECKING, iban="CH93 0076 2011 6238 5295 7", starting_balance=Decimal("0")),
        )
        cash, _ = Account.objects.get_or_create(
            name="Bargeld", defaults=dict(account_type=Account.AccountType.CASH, starting_balance=Decimal("120"))
        )

        cats_data = [
            ("Miete", Category.Kind.FIXED, 1450, "immoscout, hausverwaltung, miete"),
            ("Krankenkasse", Category.Kind.FIXED, 320, "css, helsana, swica, krankenkasse"),
            ("Internet & Handy", Category.Kind.FIXED, 75, "swisscom, sunrise, salt"),
            ("Versicherungen", Category.Kind.FIXED, 90, "axa, zurich versicherung, mobiliar"),
            ("Lebensmittel", Category.Kind.VARIABLE, 500, "migros, coop, denner, aldi, lidl"),
            ("Ausgehen & Freizeit", Category.Kind.VARIABLE, 200, "restaurant, bar, kino, netflix"),
            ("Transport", Category.Kind.VARIABLE, 120, "sbb, öv, tankstelle, migrol"),
            ("Gesundheit", Category.Kind.VARIABLE, 60, "apotheke, arzt"),
            ("Notgroschen", Category.Kind.SAVINGS, 100, ""),
            ("Lohn", Category.Kind.INCOME, 0, "lohn, salaire, gehalt"),
        ]
        colors = ["#3A6B5E", "#B9812E", "#6C7A99", "#A6432E", "#7C9885", "#C68A3D"]
        categories = {}
        for i, (name, kind, budget, keywords) in enumerate(cats_data):
            cat, _ = Category.objects.get_or_create(
                name=name,
                defaults=dict(
                    kind=kind,
                    monthly_budget=Decimal(str(budget)),
                    keywords=keywords,
                    color=colors[i % len(colors)],
                ),
            )
            categories[name] = cat

        today = date.today()
        first_of_month = today.replace(day=1)

        demo_txns = [
            (-1450, "Mietzins September", "Hausverwaltung Muster AG", categories["Miete"], 3),
            (-320, "Krankenkassenprämie", "CSS Versicherung", categories["Krankenkasse"], 4),
            (-75, "Swisscom Abo", "Swisscom AG", categories["Internet & Handy"], 5),
            (4200, "Lohn September", "Arbeitgeber AG", categories["Lohn"], 1),
            (-84.30, "Wocheneinkauf", "Migros", categories["Lebensmittel"], 2),
            (-42.10, "Einkauf", "Coop", categories["Lebensmittel"], 8),
            (-65.00, "Abendessen", "Restaurant Rössli", categories["Ausgehen & Freizeit"], 9),
            (-15.90, "Netflix Abo", "Netflix", categories["Ausgehen & Freizeit"], 10),
            (-49.00, "GA Halbtax", "SBB", categories["Transport"], 6),
            (-28.50, "Tanken", "Migrol", categories["Transport"], 12),
            (-32.00, "Medikamente", "Apotheke Zentral", categories["Gesundheit"], 14),
            (-100, "Notgroschen", "intern", categories["Notgroschen"], 15),
        ]
        for amount, descr, party, cat, day_offset in demo_txns:
            txn_date = first_of_month + timedelta(days=min(day_offset, 27))
            Transaction.objects.get_or_create(
                account=checking,
                date=txn_date,
                amount=Decimal(str(amount)),
                description=descr,
                defaults=dict(counterparty=party, category=cat),
            )

        if not Debt.objects.exists():
            # current_balance ist der Stand VOR den Beispiel-Tilgungen unten, da diese
            # als Buchungen auf dem automatisch angelegten Schulden-Umschlag erfasst
            # werden und current_balance selbst reduzieren (Transaction.save()).
            visa = Debt.objects.create(
                name="Kreditkarte Viseca",
                creditor="Viseca Card Services",
                principal=Decimal("5000"),
                current_balance=Decimal("3500"),
                interest_rate=Decimal("11.9"),
                minimum_payment=Decimal("100"),
            )
            Debt.objects.create(
                name="Kleinkredit Cembra",
                creditor="Cembra Money Bank",
                principal=Decimal("8000"),
                current_balance=Decimal("6100"),
                interest_rate=Decimal("7.5"),
                minimum_payment=Decimal("180"),
            )
            privat = Debt.objects.create(
                name="Darlehen Familie",
                creditor="Familie",
                principal=Decimal("2000"),
                current_balance=Decimal("850"),
                interest_rate=Decimal("0"),
                minimum_payment=Decimal("50"),
            )
            Transaction.objects.create(
                account=checking,
                category=visa.category,
                date=first_of_month + timedelta(days=15),
                amount=Decimal("-300"),
                description="Extra-Tilgung Kreditkarte",
                counterparty="intern",
            )
            Transaction.objects.create(
                account=checking,
                category=privat.category,
                date=today - timedelta(days=30),
                amount=Decimal("-50"),
                description="Monatsrate",
                counterparty="intern",
            )

        recurring_data = [
            ("Mietzins", categories["Miete"], Decimal("-1450"), "Hausverwaltung Muster AG", 3),
            ("Krankenkassenprämie", categories["Krankenkasse"], Decimal("-320"), "CSS Versicherung", 4),
            ("Swisscom Abo", categories["Internet & Handy"], Decimal("-75"), "Swisscom AG", 5),
            ("Lohn", categories["Lohn"], Decimal("4200"), "Arbeitgeber AG", 1),
        ]
        for descr, cat, amount, party, day in recurring_data:
            RecurringTransaction.objects.get_or_create(
                description=descr,
                account=checking,
                defaults=dict(category=cat, amount=amount, counterparty=party, day_of_month=day),
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Demo-Daten angelegt: 2 Konten, 13 Umschläge (davon 3 automatisch für Schulden), "
                "14 Buchungen, 3 Schulden, 4 Daueraufträge."
            )
        )
