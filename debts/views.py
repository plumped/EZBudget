from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .models import Debt, DebtPayment
from .services import simulate_payoff


def debt_list(request):
    strategy = request.GET.get("strategy", "avalanche")
    if strategy not in ("avalanche", "snowball"):
        strategy = "avalanche"
    extra_raw = request.GET.get("extra", "0").replace(",", ".")
    try:
        extra_budget = Decimal(extra_raw)
    except InvalidOperation:
        extra_budget = Decimal("0")

    debts = Debt.objects.filter(is_paid_off=False)
    total_balance = sum((d.current_balance for d in debts), Decimal("0"))
    total_minimum = sum((d.minimum_payment for d in debts), Decimal("0"))

    debt_dicts = [
        {
            "id": d.id,
            "name": d.name,
            "balance": d.current_balance,
            "rate": d.interest_rate,
            "minimum": d.minimum_payment,
        }
        for d in debts
    ]

    result = simulate_payoff(
        debt_dicts, strategy=strategy, extra_budget=extra_budget, start_date=date.today()
    )

    # Chart-Daten: Gesamtsaldo pro Monat (max. alle 3 Monate für Lesbarkeit bei langen Plänen)
    chart_labels = [f"M{row['month']}" for row in result.schedule]
    chart_values = [float(row["total_balance"]) for row in result.schedule]

    context = {
        "debts": debts,
        "all_debts": Debt.objects.all(),
        "strategy": strategy,
        "extra_budget": extra_budget,
        "total_balance": total_balance,
        "total_minimum": total_minimum,
        "total_monthly": total_minimum + extra_budget,
        "result": result,
        "chart_labels": chart_labels,
        "chart_values": chart_values,
    }
    return render(request, "debts/debt_list.html", context)


def debt_add(request):
    if request.method == "POST":

        def dec(name):
            return Decimal(request.POST.get(name, "0").replace(",", "."))

        Debt.objects.create(
            name=request.POST.get("name"),
            creditor=request.POST.get("creditor", ""),
            principal=dec("principal"),
            current_balance=dec("current_balance"),
            interest_rate=dec("interest_rate"),
            minimum_payment=dec("minimum_payment"),
        )
        messages.success(request, "Schuld hinzugefügt.")
        return redirect("debts:debt_list")
    return render(request, "debts/debt_form.html")


def debt_detail(request, pk):
    debt = get_object_or_404(Debt, pk=pk)
    if request.method == "POST":
        amount = Decimal(request.POST.get("amount", "0").replace(",", "."))
        DebtPayment.objects.create(
            debt=debt,
            date=request.POST.get("date") or date.today(),
            amount=amount,
            note=request.POST.get("note", ""),
        )
        messages.success(request, "Zahlung erfasst.")
        return redirect("debts:debt_detail", pk=pk)
    return render(
        request,
        "debts/debt_detail.html",
        {"debt": debt, "payments": debt.payments.all(), "today": date.today().isoformat()},
    )


def debt_delete(request, pk):
    debt = get_object_or_404(Debt, pk=pk)
    if request.method == "POST":
        debt.delete()
        messages.success(request, "Schuld gelöscht.")
    return redirect("debts:debt_list")
