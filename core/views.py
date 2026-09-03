import calendar
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AccountForm, CategoryForm, RecurringTransactionForm, SignupForm
from .models import Account, Category, RecurringTransaction, Transaction
from .services import generate_due_recurring


def signup(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Willkommen, {user.username}!")
            return redirect("core:dashboard")
    else:
        form = SignupForm()
    return render(request, "registration/signup.html", {"form": form})


def _month_context(request):
    today = date.today()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))
    first = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year
    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year
    return {
        "year": year,
        "month": month,
        "month_name": first.strftime("%B %Y"),
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
        "days_in_month": last_day,
    }


@login_required
def dashboard(request):
    generated = generate_due_recurring()
    for txn in generated:
        messages.info(request, f"Wiederkehrende Buchung generiert: {txn.description} ({txn.amount}).")

    ctx = _month_context(request)
    year, month = ctx["year"], ctx["month"]

    accounts = Account.objects.filter(is_archived=False)
    total_balance = sum((a.balance for a in accounts), Decimal("0"))

    categories = Category.objects.filter(is_archived=False)
    fixed = [c for c in categories if c.kind == Category.Kind.FIXED]
    variable = [c for c in categories if c.kind == Category.Kind.VARIABLE]
    debt_categories = [c for c in categories if c.kind == Category.Kind.DEBT]
    savings = [c for c in categories if c.kind == Category.Kind.SAVINGS]

    def totals(cats):
        budgeted = sum((c.monthly_budget for c in cats), Decimal("0"))
        spent = sum((c.spent_in_month(year, month) for c in cats), Decimal("0"))
        return budgeted, spent

    fixed_budgeted, fixed_spent = totals(fixed)
    variable_budgeted, variable_spent = totals(variable)

    income_total = Transaction.objects.filter(
        date__year=year, date__month=month, amount__gt=0
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    expense_total = -(
        Transaction.objects.filter(date__year=year, date__month=month, amount__lt=0).aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0")
    )

    from debts.models import Debt  # local import to avoid circularity at module load

    open_debts = Debt.objects.filter(is_paid_off=False)
    total_debt = sum((d.current_balance for d in open_debts), Decimal("0"))
    total_minimum = sum((d.minimum_payment for d in open_debts), Decimal("0"))

    recent_transactions = Transaction.objects.select_related("account", "category")[:8]

    context = {
        **ctx,
        "accounts": accounts,
        "total_balance": total_balance,
        "fixed": fixed,
        "variable": variable,
        "debt_categories": debt_categories,
        "savings": savings,
        "fixed_budgeted": fixed_budgeted,
        "fixed_spent": fixed_spent,
        "variable_budgeted": variable_budgeted,
        "variable_spent": variable_spent,
        "income_total": income_total,
        "expense_total": expense_total,
        "net_total": income_total - expense_total,
        "total_debt": total_debt,
        "total_minimum": total_minimum,
        "open_debts_count": open_debts.count(),
        "recent_transactions": recent_transactions,
    }
    return render(request, "core/dashboard.html", context)


@login_required
def envelope_list(request):
    ctx = _month_context(request)
    year, month = ctx["year"], ctx["month"]
    categories = Category.objects.filter(is_archived=False)
    rows = []
    for c in categories:
        spent = c.spent_in_month(year, month)
        rows.append(
            {
                "category": c,
                "spent": spent,
                "available": c.monthly_budget - spent,
                "rollover": c.rollover_balance(year, month),
                "progress": c.progress_percent(year, month),
                "over_budget": spent > c.monthly_budget and c.monthly_budget > 0,
            }
        )
    context = {**ctx, "rows": rows}
    return render(request, "core/envelope_list.html", context)


@login_required
def envelope_detail(request, pk):
    category = get_object_or_404(Category, pk=pk)
    ctx = _month_context(request)
    year, month = ctx["year"], ctx["month"]
    transactions = category.transactions.filter(date__year=year, date__month=month)
    context = {
        **ctx,
        "category": category,
        "transactions": transactions,
        "spent": category.spent_in_month(year, month),
        "available": category.available_in_month(year, month),
        "rollover": category.rollover_balance(year, month),
        "progress": category.progress_percent(year, month),
    }
    return render(request, "core/envelope_detail.html", context)


@login_required
def transaction_list(request):
    ctx = _month_context(request)
    year, month = ctx["year"], ctx["month"]
    qs = Transaction.objects.select_related("account", "category").filter(
        date__year=year, date__month=month
    )
    category_id = request.GET.get("category")
    if category_id:
        qs = qs.filter(category_id=category_id)
    context = {**ctx, "transactions": qs, "categories": Category.objects.filter(is_archived=False)}
    return render(request, "core/transaction_list.html", context)


@login_required
def transaction_add(request):
    accounts = Account.objects.filter(is_archived=False)
    categories = Category.objects.filter(is_archived=False)
    if request.method == "POST":
        account = get_object_or_404(Account, pk=request.POST.get("account"))
        category_id = request.POST.get("category") or None
        amount_raw = request.POST.get("amount", "0").replace(",", ".")
        try:
            amount = Decimal(amount_raw)
        except Exception:
            amount = Decimal("0")
        if request.POST.get("direction") == "expense":
            amount = -abs(amount)
        else:
            amount = abs(amount)
        Transaction.objects.create(
            account=account,
            category_id=category_id,
            date=request.POST.get("date") or date.today(),
            amount=amount,
            description=request.POST.get("description", ""),
            counterparty=request.POST.get("counterparty", ""),
        )
        messages.success(request, "Buchung gespeichert.")
        return redirect("core:transaction_list")
    return render(
        request,
        "core/transaction_form.html",
        {"accounts": accounts, "categories": categories, "today": date.today().isoformat()},
    )


@login_required
def transaction_delete(request, pk):
    txn = get_object_or_404(Transaction, pk=pk)
    if request.method == "POST":
        txn.delete()
        messages.success(request, "Buchung gelöscht.")
    return redirect("core:transaction_list")


@login_required
def account_list(request):
    accounts = Account.objects.all()
    return render(request, "core/account_list.html", {"accounts": accounts})


@login_required
def account_detail(request, pk):
    account = get_object_or_404(Account, pk=pk)
    transactions = account.transactions.all()[:50]
    return render(request, "core/account_detail.html", {"account": account, "transactions": transactions})


@login_required
def account_add(request):
    if request.method == "POST":
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save()
            messages.success(request, f"Konto „{account.name}“ angelegt.")
            return redirect("core:account_list")
    else:
        form = AccountForm()
    return render(request, "core/account_form.html", {"form": form, "is_new": True})


@login_required
def account_edit(request, pk):
    account = get_object_or_404(Account, pk=pk)
    if request.method == "POST":
        form = AccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, f"Konto „{account.name}“ aktualisiert.")
            return redirect("core:account_list")
    else:
        form = AccountForm(instance=account)
    return render(request, "core/account_form.html", {"form": form, "account": account, "is_new": False})


@login_required
def account_archive_toggle(request, pk):
    account = get_object_or_404(Account, pk=pk)
    if request.method == "POST":
        account.is_archived = not account.is_archived
        account.save(update_fields=["is_archived"])
        messages.success(
            request,
            f"Konto „{account.name}“ {'archiviert' if account.is_archived else 'reaktiviert'}.",
        )
    return redirect("core:account_list")


@login_required
def envelope_add(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f"Umschlag „{category.name}“ angelegt.")
            return redirect("core:envelope_list")
    else:
        form = CategoryForm()
    return render(request, "core/envelope_form.html", {"form": form, "is_new": True})


@login_required
def envelope_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f"Umschlag „{category.name}“ aktualisiert.")
            return redirect("core:envelope_list")
    else:
        form = CategoryForm(instance=category)
    return render(request, "core/envelope_form.html", {"form": form, "category": category, "is_new": False})


@login_required
def envelope_archive_toggle(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        category.is_archived = not category.is_archived
        category.save(update_fields=["is_archived"])
        messages.success(
            request,
            f"Umschlag „{category.name}“ {'archiviert' if category.is_archived else 'reaktiviert'}.",
        )
    return redirect("core:envelope_list")


@login_required
def recurring_list(request):
    recurring = RecurringTransaction.objects.select_related("account", "category").all()
    return render(request, "core/recurring_list.html", {"recurring": recurring})


@login_required
def recurring_add(request):
    if request.method == "POST":
        form = RecurringTransactionForm(request.POST)
        if form.is_valid():
            rt = form.save()
            messages.success(request, f"Dauerauftrag „{rt.description}“ angelegt.")
            return redirect("core:recurring_list")
    else:
        form = RecurringTransactionForm()
    return render(request, "core/recurring_form.html", {"form": form, "is_new": True})


@login_required
def recurring_edit(request, pk):
    rt = get_object_or_404(RecurringTransaction, pk=pk)
    if request.method == "POST":
        form = RecurringTransactionForm(request.POST, instance=rt)
        if form.is_valid():
            form.save()
            messages.success(request, f"Dauerauftrag „{rt.description}“ aktualisiert.")
            return redirect("core:recurring_list")
    else:
        form = RecurringTransactionForm(instance=rt)
    return render(request, "core/recurring_form.html", {"form": form, "recurring": rt, "is_new": False})


@login_required
def recurring_delete(request, pk):
    rt = get_object_or_404(RecurringTransaction, pk=pk)
    if request.method == "POST":
        rt.delete()
        messages.success(request, f"Dauerauftrag „{rt.description}“ gelöscht.")
    return redirect("core:recurring_list")


@login_required
def recurring_generate(request):
    if request.method == "POST":
        created = generate_due_recurring()
        if created:
            messages.success(request, f"{len(created)} Buchung(en) generiert.")
        else:
            messages.info(request, "Keine fälligen wiederkehrenden Buchungen.")
    return redirect("core:recurring_list")
