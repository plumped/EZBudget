"""Schulden-Tilgungsplan: Avalanche- und Snowball-Strategie."""
import datetime
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class SimResult:
    months: int
    total_interest: Decimal
    payoff_order: list
    schedule: list  # [{month, date, total_balance}]
    debt_free_date: object = None
    reached_max: bool = False


def _add_months(base_date, months):
    year = base_date.year + (base_date.month - 1 + months) // 12
    month = (base_date.month - 1 + months) % 12 + 1
    return datetime.date(year, month, 1)


def simulate_payoff(debts, strategy="avalanche", extra_budget=Decimal("0"), max_months=600, start_date=None):
    """
    debts: iterable of dicts {id, name, balance, rate, minimum}
        rate = jährlicher Zinssatz in Prozent (z.B. 8.5)
    strategy: 'avalanche' (höchster Zins zuerst) oder 'snowball' (kleinste Restschuld zuerst)
    extra_budget: zusätzlicher monatlicher Betrag OBERHALB der Summe aller Mindestraten
    """
    snap = []
    for d in debts:
        if Decimal(d["balance"]) <= 0:
            continue
        snap.append(
            {
                "id": d["id"],
                "name": d["name"],
                "balance": Decimal(d["balance"]),
                "rate": Decimal(d["rate"]),
                "minimum": Decimal(d["minimum"]),
            }
        )

    if not snap:
        return SimResult(months=0, total_interest=Decimal("0"), payoff_order=[], schedule=[])

    def sort_key(d):
        return d["balance"] if strategy == "snowball" else -d["rate"]

    # Tilgungsreihenfolge = mit welcher Schuld die gewählte Strategie JETZT beginnt.
    # Bewusst aus dem heutigen Stand berechnet statt aus dem simulierten Abschlussdatum:
    # bei kleinem Extra-Budget dominiert die natürliche Amortisation über die Mindestraten
    # so stark, dass beide Strategien zufällig dieselbe Reihenfolge fertigstellen können,
    # obwohl sie das Extra-Budget unterschiedlich priorisieren — die Reihenfolge, in der
    # priorisiert wird, muss beim Umschalten aber immer sichtbar wechseln.
    payoff_order = [d["name"] for d in sorted(snap, key=sort_key)]

    total_interest = Decimal("0")
    months = 0
    schedule = []
    already_off = set()
    # Mindestraten bereits getilgter Schulden werden nicht einfach eingespart, sondern
    # ab dem Folgemonat zusätzlich zum Extra-Budget verteilt ("Schneeball-Effekt") —
    # das ist der eigentliche Kern von Avalanche/Snowball, nicht nur die Priorität.
    released_minimums = Decimal("0")

    while any(d["balance"] > 0 for d in snap) and months < max_months:
        months += 1

        # 1) Monatszins gutschreiben
        for d in snap:
            if d["balance"] > 0:
                interest = d["balance"] * (d["rate"] / Decimal("100") / Decimal("12"))
                d["balance"] += interest
                total_interest += interest

        # 2) Mindestraten zahlen
        for d in snap:
            if d["balance"] <= 0:
                continue
            pay = min(d["minimum"], d["balance"])
            d["balance"] -= pay

        # 3) Restbudget (Extra-Budget + freigewordene Mindestraten) nach Priorität verteilen
        pool = Decimal(extra_budget) + released_minimums
        ordered = sorted([d for d in snap if d["balance"] > 0], key=sort_key)
        for d in ordered:
            if pool <= 0:
                break
            pay = min(pool, d["balance"])
            d["balance"] -= pay
            pool -= pay

        for d in snap:
            if d["balance"] < 0:
                d["balance"] = Decimal("0")
            if d["balance"] == 0 and d["id"] not in already_off:
                already_off.add(d["id"])
                released_minimums += d["minimum"]

        schedule.append(
            {
                "month": months,
                "date": _add_months(start_date, months).isoformat() if start_date else None,
                "total_balance": sum((d["balance"] for d in snap), Decimal("0")),
                "balances": {d["id"]: d["balance"] for d in snap},
            }
        )

    debt_free_date = None
    if start_date is not None and months < max_months:
        debt_free_date = _add_months(start_date, months)

    return SimResult(
        months=months,
        total_interest=total_interest,
        payoff_order=payoff_order,
        schedule=schedule,
        debt_free_date=debt_free_date,
        reached_max=months >= max_months,
    )
