"""Budget-Monat = Kalendermonat, optional verschoben auf einen anderen Starttag
(z.B. Lohn/Daueraufträge am 25., dann läuft der Budget-Monat vom 25. bis zum 24.
des Folgemonats). Ein Budget-Monat wird weiterhin durch ein (Jahr, Monat)-Paar
identifiziert — nämlich den Kalendermonat, in dem er beginnt — nur die tatsächlichen
Datumsgrenzen verschieben sich.
"""
import calendar
from datetime import date, timedelta

from .models import BudgetSettings


def get_month_start_day():
    return BudgetSettings.load().month_start_day


def _period_start(year, month, start_day):
    if start_day <= 1:
        return date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(start_day, last_day))


def budget_period_bounds(year, month, start_day=None):
    """Gibt (start, end) des Budget-Monats zurück, der im Kalendermonat
    `month`/`year` beginnt — beide Grenzen inklusive."""
    if start_day is None:
        start_day = get_month_start_day()
    start = _period_start(year, month, start_day)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    next_start = _period_start(next_year, next_month, start_day)
    end = next_start - timedelta(days=1)
    return start, end


def budget_period_for_date(d, start_day=None):
    """Gibt (year, month) des Budget-Monats zurück, in dem das Datum `d` liegt."""
    if start_day is None:
        start_day = get_month_start_day()
    if start_day <= 1 or d.day >= start_day:
        return d.year, d.month
    prev_year, prev_month = (d.year - 1, 12) if d.month == 1 else (d.year, d.month - 1)
    return prev_year, prev_month
