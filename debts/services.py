"""Schulden-Tilgungsplan: Avalanche- und Snowball-Strategie."""
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class SimResult:
    months: int
    total_interest: Decimal
    payoff_order: list
    schedule: list  # [{month, total_balance}]
    debt_free_date: object = None
    reached_max: bool = False


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

    total_interest = Decimal("0")
    months = 0
    schedule = []
    payoff_order = []
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
                payoff_order.append(d["name"])
                released_minimums += d["minimum"]

        schedule.append(
            {
                "month": months,
                "total_balance": sum((d["balance"] for d in snap), Decimal("0")),
                "balances": {d["id"]: d["balance"] for d in snap},
            }
        )

    debt_free_date = None
    if start_date is not None and months < max_months:
        year = start_date.year + (start_date.month - 1 + months) // 12
        month = (start_date.month - 1 + months) % 12 + 1
        import datetime

        debt_free_date = datetime.date(year, month, 1)

    return SimResult(
        months=months,
        total_interest=total_interest,
        payoff_order=payoff_order,
        schedule=schedule,
        debt_free_date=debt_free_date,
        reached_max=months >= max_months,
    )
