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
    emergency_fund_total: Decimal = Decimal("0")
    emergency_fund_filled_date: object = None


def _add_months(base_date, months):
    year = base_date.year + (base_date.month - 1 + months) // 12
    month = (base_date.month - 1 + months) % 12 + 1
    return datetime.date(year, month, 1)


def simulate_payoff(
    debts, strategy="avalanche", extra_budget=Decimal("0"), max_months=600, start_date=None,
    emergency_fund_gap=Decimal("0"),
):
    """
    debts: iterable of dicts {id, name, balance, rate, minimum, max_extra}
        rate = jährlicher Zinssatz in Prozent (z.B. 8.5)
        max_extra = maximale monatliche Zuzahlung über die Mindestrate hinaus, die dieser
            Kredit erlaubt (None/fehlend = unbegrenzt, 0 = keine Zuzahlung möglich, z.B. ein
            Ratenkredit mit fixem Tilgungsplan). Optional, für Rückwärtskompatibilität.
    strategy: 'avalanche' (höchster Zins zuerst) oder 'snowball' (kleinste Restschuld zuerst)
    extra_budget: zusätzlicher monatlicher Betrag OBERHALB der Summe aller Mindestraten
    emergency_fund_gap: fehlender Betrag bis zum Notfallfonds-Sparziel (siehe
        emergency_fund_status()) — bewährtes Prinzip aus der Schuldenberatung: bevor
        Extra-Budget auf Schulden verteilt wird, füllt es zuerst diese Lücke, damit die
        nächste unerwartete Rechnung nicht wieder auf der Kreditkarte landet. 0 (Default)
        = kein Notfallfonds markiert oder bereits voll, verhält sich dann wie zuvor.
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
    emergency_fund_remaining = Decimal(emergency_fund_gap)
    emergency_fund_total = Decimal("0")
    emergency_fund_filled_date = None

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

        # Notfallfonds-Priorität: bevor irgendetwas an Schulden geht, füllt das
        # Restbudget zuerst die Lücke zum Sparziel des Notfallfonds (falls markiert
        # und noch nicht voll) — siehe emergency_fund_gap oben.
        if emergency_fund_remaining > 0 and pool > 0:
            diverted = min(pool, emergency_fund_remaining)
            pool -= diverted
            emergency_fund_remaining -= diverted
            emergency_fund_total += diverted
            if emergency_fund_remaining <= 0 and emergency_fund_filled_date is None and start_date is not None:
                emergency_fund_filled_date = _add_months(start_date, months)

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
        emergency_fund_total=emergency_fund_total,
        emergency_fund_filled_date=emergency_fund_filled_date,
    )


@dataclass
class SweepAllocation:
    allocations: list  # [{"id", "name", "amount": Decimal}]
    unallocated: Decimal = Decimal("0")
    to_emergency_fund: Decimal = Decimal("0")


def allocate_extra_once(debts, strategy="avalanche", extra_budget=Decimal("0"), emergency_fund_gap=Decimal("0")):
    """Verteilt einen EINMALIGEN Extra-Betrag (z.B. übriges Monatsbudget) nach
    Priorität auf die aktuellen Restschulden — dieselbe Kappungs-/Rollover-Logik wie
    Schritt 3 in simulate_payoff() (siehe dort für die ausführliche Begründung),
    hier aber für einen einzelnen Moment statt eine Mehrmonatssimulation, bewusst
    als eigenständige, einfachere Funktion statt geteiltem Code, um die bereits
    gut getestete Mehrmonatsschleife nicht anzufassen.

    emergency_fund_gap: siehe simulate_payoff() — wird vor jeder Schuld zuerst bedient.

    Die App löst dabei KEINE echte Überweisung aus — sie kann nur vorschlagen,
    wie sich ein Betrag verteilen würde, den der Nutzer selbst bei seiner Bank
    überweist und danach hier als Zahlung erfasst.
    """
    pool = Decimal(extra_budget)
    to_emergency_fund = Decimal("0")
    if pool > 0 and emergency_fund_gap > 0:
        to_emergency_fund = min(pool, Decimal(emergency_fund_gap))
        pool -= to_emergency_fund

    snap = []
    for d in debts:
        balance = Decimal(d["balance"])
        if balance <= 0:
            continue
        max_extra = d.get("max_extra")
        snap.append(
            {
                "id": d["id"],
                "name": d["name"],
                "balance": balance,
                "rate": Decimal(d["rate"]),
                "max_extra": Decimal(max_extra) if max_extra is not None else None,
            }
        )

    if pool <= 0 or not snap:
        return SweepAllocation(
            allocations=[], unallocated=max(pool, Decimal("0")), to_emergency_fund=to_emergency_fund
        )

    # Anders als in simulate_payoff() zählt hier JEDER Rest als "nicht zugeteilt" —
    # ob wegen einer Kappungsgrenze oder schlicht, weil die Restschuld insgesamt
    # kleiner ist als der verfügbare Betrag (dann ist das keine Auffälligkeit,
    # sondern schlicht mehr Überschuss, als aktuell gebraucht wird). Für einen
    # einzelnen Verteilungsvorschlag ist diese Unterscheidung nicht relevant — der
    # Nutzer soll so oder so sehen, wie viel des Überschusses nicht Teil des
    # Vorschlags ist.
    sort_key = (lambda d: d["balance"]) if strategy == "snowball" else (lambda d: -d["rate"])
    ordered = sorted(snap, key=sort_key)

    allocations = []
    for d in ordered:
        if pool <= 0:
            break
        cap = pool if d["max_extra"] is None else min(pool, d["max_extra"])
        pay = min(pool, d["balance"], cap)
        if pay > 0:
            allocations.append({"id": d["id"], "name": d["name"], "amount": pay})
        pool -= pay
    return SweepAllocation(allocations=allocations, unallocated=pool, to_emergency_fund=to_emergency_fund)


def eligible_envelope_surplus(year, month):
    """Positiver Übertrag aus Umschlägen, der sich theoretisch für eine
    Zusatztilgung nutzen liesse — alle nicht archivierten Umschläge ausser
    Einnahmen, Schulden-Umschlägen selbst und Umschlägen mit eigenem Sparziel
    (target_amount), die bewusst für etwas anderes zurückgelegt werden. Nur der
    POSITIVE Übertrag zählt; ein überzogener Umschlag mindert das Ergebnis nicht.

    Gibt (total, sources) zurück, sources = [{"id", "name", "amount": Decimal}].
    """
    from core.models import Category

    categories = Category.objects.filter(is_archived=False, target_amount__isnull=True).exclude(
        kind__in=[Category.Kind.DEBT, Category.Kind.INCOME]
    )
    sources = []
    total = Decimal("0")
    for c in categories:
        balance = c.rollover_balance(year, month)
        if balance > 0:
            sources.append({"id": c.id, "name": c.name, "amount": balance})
            total += balance
    return total, sources


def emergency_fund_status(year, month):
    """Der als Notfallfonds markierte Umschlag (falls vorhanden) und wie weit er
    noch von seinem Sparziel entfernt ist — bewährtes Prinzip aus der
    Schuldenberatung: erst einen Puffer aufbauen, bevor Extra-Budget aggressiv auf
    Schulden verteilt wird, sonst landet die nächste unerwartete Rechnung wieder
    auf der Kreditkarte.

    Gibt (category_or_None, target, current, gap) zurück. Ohne markierten
    Notfallfonds (oder ohne gesetztes Sparziel) ist gap immer 0 — die Priorisierung
    ist rein opt-in und ändert für alle anderen nichts am bisherigen Verhalten.
    """
    from core.models import Category

    fund = Category.objects.filter(is_emergency_fund=True, is_archived=False).first()
    if fund is None or not fund.target_amount:
        return None, Decimal("0"), Decimal("0"), Decimal("0")
    current = fund.rollover_balance(year, month)
    gap = max(Decimal("0"), fund.target_amount - current)
    return fund, fund.target_amount, current, gap


SWEEP_WINDOW_DAYS = 5


def sweep_window_status(today, month_start_day):
    """Ob der Monatsende-Sweep-Vorschlag heute sinnvoll anzeigbar ist.

    Umschlag-Überträge (rollover_balance) wachsen im Laufe des Budget-Monats
    einfach an, weil noch nicht alles ausgegeben wurde — das ist am 5. Tag des
    Monats kein "Überschuss", sondern Geld, das man diesen Monat noch braucht.
    Der Vorschlag ist deshalb nur in den letzten SWEEP_WINDOW_DAYS Tagen des
    Budget-Monats sinnvoll, wenn ein verbleibender Übertrag tatsächlich eher
    ungenutztes Budget ist statt einfach "noch nicht ausgegeben".

    Gibt (year, month, days_remaining, in_window) zurück — year/month ist der
    Budget-Monat, in dem `today` liegt.
    """
    from core.budget_month import budget_period_bounds, budget_period_for_date

    year, month = budget_period_for_date(today, month_start_day)
    _, period_end = budget_period_bounds(year, month, month_start_day)
    days_remaining = (period_end - today).days
    return year, month, days_remaining, days_remaining <= SWEEP_WINDOW_DAYS


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


MILESTONE_THRESHOLDS = [25, 50, 75, 100]


def check_new_milestones():
    """Meldet neu erreichte Tilgungs-Meilensteine (25/50/75/100%) seit dem letzten
    Aufruf — als kleine Motivations-Momente auf dem Dashboard.

    Bewusst zustandsbehaftet (Debt.last_milestone_reached), nicht einfach live aus
    progress_percent berechnet: sonst würde dieselbe Meldung bei jedem
    Dashboard-Aufruf erneut erscheinen, solange die Schuld über der Schwelle bleibt.
    Springt eine Zahlung über mehrere Schwellen auf einmal (z.B. von 20% direkt auf
    100%), wird nur der höchste neu erreichte Meilenstein gemeldet — das ist der
    einzige, der für den Nutzer gerade relevant ist.

    Gibt eine Liste von {"debt_id", "debt_name", "milestone"} zurück, eine pro
    Schuld mit neu erreichtem Meilenstein seit dem letzten Aufruf.
    """
    from .models import Debt

    newly_reached = []
    for debt in Debt.objects.all():
        reached = [m for m in MILESTONE_THRESHOLDS if debt.progress_percent >= m]
        if not reached:
            continue
        highest = reached[-1]
        if highest > debt.last_milestone_reached:
            newly_reached.append({"debt_id": debt.id, "debt_name": debt.name, "milestone": highest})
            Debt.objects.filter(pk=debt.id).update(last_milestone_reached=highest)

    return newly_reached
