"""Schulden-Tilgungsplan: Avalanche- und Snowball-Strategie."""
import datetime
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal


@dataclass
class SimResult:
    months: int
    total_interest: Decimal
    payoff_order: list
    schedule: list  # [{month, date, total_balance}]
    debt_free_date: object = None
    reached_max: bool = False
    unallocated_extra: Decimal = Decimal("0")


def _add_months(base_date, months):
    year = base_date.year + (base_date.month - 1 + months) // 12
    month = (base_date.month - 1 + months) % 12 + 1
    return datetime.date(year, month, 1)


def simulate_payoff(debts, strategy="avalanche", extra_budget=Decimal("0"), max_months=600, start_date=None):
    """
    debts: iterable of dicts {id, name, balance, rate, minimum, max_extra}
        rate = jährlicher Zinssatz in Prozent (z.B. 8.5)
        max_extra = maximale monatliche Zuzahlung über die Mindestrate hinaus, die dieser
            Kredit erlaubt (None/fehlend = unbegrenzt, 0 = keine Zuzahlung möglich, z.B. ein
            Ratenkredit mit fixem Tilgungsplan). Optional, für Rückwärtskompatibilität.
    strategy: 'avalanche' (höchster Zins zuerst) oder 'snowball' (kleinste Restschuld zuerst)
    extra_budget: zusätzlicher monatlicher Betrag OBERHALB der Summe aller Mindestraten
    """
    snap = []
    for d in debts:
        if Decimal(d["balance"]) <= 0:
            continue
        max_extra = d.get("max_extra")
        snap.append(
            {
                "id": d["id"],
                "name": d["name"],
                "balance": Decimal(d["balance"]),
                "rate": Decimal(d["rate"]),
                "minimum": Decimal(d["minimum"]),
                "max_extra": Decimal(max_extra) if max_extra is not None else None,
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
    unallocated_extra = Decimal("0")

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

        # 3) Restbudget (Extra-Budget + freigewordene Mindestraten) nach Priorität verteilen.
        # Manche Kredite (z.B. ein Ratenkredit mit fixem Tilgungsplan) erlauben keine oder nur
        # eine gedeckelte Zuzahlung über die Mindestrate hinaus (max_extra) — was ein gedeckelter
        # Kredit nicht aufnehmen kann, fliesst an die nächste Schuld in der Prioritätsreihenfolge;
        # was am Ende nirgends platziert werden kann, wird als unallocated_extra gemeldet statt
        # stillschweigend zu verfallen. Restbudget, das übrig bleibt, WEIL schlicht keine Schuld
        # mehr offen ist (normales Ende der Tilgung), ist dagegen kein "blockierter" Betrag —
        # das war schon vor max_extra so und ist einfach frei gewordenes Geld, keine Auffälligkeit.
        pool = Decimal(extra_budget) + released_minimums
        ordered = sorted([d for d in snap if d["balance"] > 0], key=sort_key)
        total_capacity = sum((d["balance"] for d in ordered), Decimal("0"))
        natural_leftover = max(Decimal("0"), pool - total_capacity)
        for d in ordered:
            if pool <= 0:
                break
            cap = pool if d["max_extra"] is None else min(pool, d["max_extra"])
            pay = min(pool, d["balance"], cap)
            d["balance"] -= pay
            pool -= pay
        unallocated_extra += max(Decimal("0"), pool - natural_leftover)

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
        unallocated_extra=unallocated_extra,
    )


def accrue_monthly_interest(today=None):
    """Bucht den monatlichen Zins EINMAL pro Kalendermonat und Schuld — echt auf
    current_balance, nicht nur in der simulate_payoff()-Projektion oben.

    Bei einer kontoverknüpften Schuld (z.B. Kreditkarte, siehe Debt.account) als
    echte, sichtbare Buchung auf diesem Konto — current_balance folgt danach
    automatisch über Transaction.save() (Transaction._linked_debt_via_account()).
    Duplikatschutz dabei bewusst über die Existenz dieser Buchung (import_ref), nicht
    nur über last_interest_year/-month: löscht jemand die Buchung wieder, muss der
    Zins erneut buchbar sein, statt bis zum nächsten Monat zu fehlen.

    Ohne Kontoverknüpfung (klassische Schuld ohne laufende Kreditlinie) direkt auf
    current_balance, da keine echte Kontobewegung stattfindet — hier über
    last_interest_year/-month dedupliziert.
    """
    from core.models import Transaction

    from .models import Debt

    today = today or datetime.date.today()
    year, month = today.year, today.month
    accrued = []

    for debt in Debt.objects.filter(is_paid_off=False):
        interest = (debt.current_balance * debt.interest_rate / Decimal("100") / Decimal("12")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if interest <= 0:
            continue

        if debt.account_id:
            ref = f"debt-interest-{debt.id}-{year}-{month:02d}"
            if Transaction.objects.filter(import_ref=ref).exists():
                continue
            Transaction.objects.create(
                account_id=debt.account_id,
                date=today,
                amount=-interest,
                description=f"Zinsen {debt.name}",
                import_ref=ref,
            )
            Debt.objects.filter(pk=debt.id).update(last_interest_year=year, last_interest_month=month)
        else:
            if (debt.last_interest_year, debt.last_interest_month) == (year, month):
                continue
            debt.current_balance = debt.current_balance + interest
            debt.last_interest_year = year
            debt.last_interest_month = month
            debt.save(update_fields=["current_balance", "last_interest_year", "last_interest_month"])
        accrued.append(debt)

    return accrued
