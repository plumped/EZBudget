from datetime import date
from decimal import Decimal

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import transaction as db_transaction
from django.db.models import Q, Sum
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .budget_month import budget_period_bounds, budget_period_for_date, get_month_start_day
from .models import Account, BudgetSettings, Category, RecurringTransaction, Transaction
from .serializers import (
    AccountSerializer,
    BudgetSettingsSerializer,
    CategorySerializer,
    LoginSerializer,
    RecurringTransactionSerializer,
    SignupSerializer,
    TransactionSerializer,
    TransferSerializer,
    UserSerializer,
)
from .services import generate_due_recurring


def _month_bounds(year, month):
    first, last = budget_period_bounds(year, month)
    days_in_period = (last - first).days + 1
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1
    return first, last, days_in_period, (prev_year, prev_month), (next_year, next_month)


def _requested_year_month(request):
    today = date.today()
    try:
        year = int(request.query_params.get("year", today.year))
        month = int(request.query_params.get("month", today.month))
    except (TypeError, ValueError):
        year, month = today.year, today.month
    return year, month


@method_decorator(ensure_csrf_cookie, name="get")
class CsrfView(APIView):
    """Setzt das csrftoken-Cookie, damit das Frontend es für spätere
    POST/PUT/DELETE-Requests als X-CSRFToken-Header mitschicken kann."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response({"detail": "Benutzername oder Passwort ist falsch."}, status=status.HTTP_400_BAD_REQUEST)
        login(request, user)
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class SettingsView(APIView):
    def get(self, request):
        return Response(BudgetSettingsSerializer(BudgetSettings.load()).data)

    def put(self, request):
        serializer = BudgetSettingsSerializer(BudgetSettings.load(), data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer

    def get_queryset(self):
        qs = Account.objects.all()
        if self.request.query_params.get("active_only") == "1":
            qs = qs.filter(is_archived=False)
        return qs

    @action(detail=True, methods=["post"])
    def archive_toggle(self, request, pk=None):
        account = self.get_object()
        account.is_archived = not account.is_archived
        account.save(update_fields=["is_archived"])
        return Response(self.get_serializer(account).data)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_queryset(self):
        qs = Category.objects.all()
        if self.request.query_params.get("active_only") == "1":
            qs = qs.filter(is_archived=False)
        return qs

    @action(detail=True, methods=["post"])
    def archive_toggle(self, request, pk=None):
        category = self.get_object()
        category.is_archived = not category.is_archived
        category.save(update_fields=["is_archived"])
        return Response(self.get_serializer(category).data)


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.select_related("account", "category")
    serializer_class = TransactionSerializer

    def get_queryset(self):
        qs = Transaction.objects.select_related("account", "category").all()
        params = self.request.query_params
        date_from = params.get("date_from")
        date_to = params.get("date_to")
        if date_from or date_to:
            # Expliziter Datumsbereich ersetzt den Monatsfilter — so kann über den
            # aktuell gewählten Budget-Monat hinaus gesucht werden.
            if date_from:
                qs = qs.filter(date__gte=date_from)
            if date_to:
                qs = qs.filter(date__lte=date_to)
        elif params.get("year") and params.get("month"):
            start, end = budget_period_bounds(int(params["year"]), int(params["month"]))
            qs = qs.filter(date__gte=start, date__lte=end)
        if params.get("category"):
            if params["category"] == "none":
                qs = qs.filter(category__isnull=True)
            else:
                qs = qs.filter(category_id=params["category"])
        if params.get("account"):
            qs = qs.filter(account_id=params["account"])
        if params.get("search"):
            search = params["search"]
            qs = qs.filter(Q(description__icontains=search) | Q(counterparty__icontains=search))
        return qs


class TransferView(APIView):
    """Erstellt einen Konto-zu-Konto-Transfer als zwei verknüpfte, umschlaglose
    Buchungen — spart Geld verschieben, ohne es fälschlich als Einnahme/Ausgabe in
    Umschlägen oder im Dashboard-Total zu zählen (siehe DashboardView)."""

    def post(self, request):
        serializer = TransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        from_account = data["from_account"]
        to_account = data["to_account"]
        note = data["note"]

        with db_transaction.atomic():
            out_txn = Transaction.objects.create(
                account=from_account,
                date=data["date"],
                amount=-data["amount"],
                description=note or f"Transfer zu {to_account.name}",
                counterparty=to_account.name,
            )
            in_txn = Transaction.objects.create(
                account=to_account,
                date=data["date"],
                amount=data["amount"],
                description=note or f"Transfer von {from_account.name}",
                counterparty=from_account.name,
            )
            out_txn.transfer_pair = in_txn
            in_txn.transfer_pair = out_txn
            out_txn.save(update_fields=["transfer_pair"])
            in_txn.save(update_fields=["transfer_pair"])

        ctx = {"request": request}
        return Response(
            {"out": TransactionSerializer(out_txn, context=ctx).data, "in": TransactionSerializer(in_txn, context=ctx).data},
            status=status.HTTP_201_CREATED,
        )


class RecurringTransactionViewSet(viewsets.ModelViewSet):
    queryset = RecurringTransaction.objects.select_related("account", "category")
    serializer_class = RecurringTransactionSerializer

    @action(detail=False, methods=["post"])
    def generate(self, request):
        created = generate_due_recurring()
        return Response(
            {
                "created_count": len(created),
                "transactions": TransactionSerializer(created, many=True, context={"request": request}).data,
            }
        )


class DashboardView(APIView):
    def get(self, request):
        generated = generate_due_recurring()

        from debts.services import accrue_monthly_interest

        accrue_monthly_interest()

        year, month = _requested_year_month(request)
        first, last, days_in_month, (prev_year, prev_month), (next_year, next_month) = _month_bounds(year, month)

        accounts = Account.objects.filter(is_archived=False)
        total_balance = sum((a.balance for a in accounts), Decimal("0"))

        categories = Category.objects.filter(is_archived=False)
        ctx = {"request": request}

        def serialize_kind(kind):
            cats = [c for c in categories if c.kind == kind]
            budgeted = sum((c.monthly_budget for c in cats), Decimal("0"))
            spent = sum((c.spent_in_month(year, month) for c in cats), Decimal("0"))
            return {
                "budgeted": str(budgeted),
                "spent": str(spent),
                "categories": CategorySerializer(cats, many=True, context=ctx).data,
            }

        # Transfers zwischen eigenen Konten ausgeschlossen — sonst würden sie das
        # Einnahmen-/Ausgaben-Total verzerren, obwohl kein Geld den Haushalt verlässt.
        income_total = Transaction.objects.filter(
            date__gte=first, date__lte=last, amount__gt=0, transfer_pair__isnull=True
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        expense_total = -(
            Transaction.objects.filter(
                date__gte=first, date__lte=last, amount__lt=0, transfer_pair__isnull=True
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0")
        )

        from debts.models import Debt

        open_debts = Debt.objects.filter(is_paid_off=False)
        total_debt = sum((d.current_balance for d in open_debts), Decimal("0"))
        total_minimum = sum((d.minimum_payment for d in open_debts), Decimal("0"))

        recent_transactions = Transaction.objects.select_related("account", "category")[:8]

        # Transfers sind absichtlich ohne Umschlag (siehe TransferView) — zählen hier nicht als
        # "vergessen", nur echte Buchungen ohne Zuordnung sollen die Warnung auslösen.
        uncategorized_count = Transaction.objects.filter(
            date__gte=first, date__lte=last, category__isnull=True, transfer_pair__isnull=True
        ).count()

        return Response(
            {
                "year": year,
                "month": month,
                "month_name": first.strftime("%B %Y"),
                "period_start": first.isoformat(),
                "period_end": last.isoformat(),
                "prev": {"year": prev_year, "month": prev_month},
                "next": {"year": next_year, "month": next_month},
                "days_in_month": days_in_month,
                "total_balance": str(total_balance),
                "income_total": str(income_total),
                "expense_total": str(expense_total),
                "net_total": str(income_total - expense_total),
                "fixed": serialize_kind(Category.Kind.FIXED),
                "variable": serialize_kind(Category.Kind.VARIABLE),
                "debt_categories": CategorySerializer(
                    [c for c in categories if c.kind == Category.Kind.DEBT], many=True, context=ctx
                ).data,
                "savings": CategorySerializer(
                    [c for c in categories if c.kind == Category.Kind.SAVINGS], many=True, context=ctx
                ).data,
                "total_debt": str(total_debt),
                "total_minimum": str(total_minimum),
                "open_debts_count": open_debts.count(),
                "recent_transactions": TransactionSerializer(recent_transactions, many=True, context=ctx).data,
                "generated_recurring": TransactionSerializer(generated, many=True, context=ctx).data,
                "uncategorized_count": uncategorized_count,
            }
        )


class TrendsView(APIView):
    """Verlaufsdaten über mehrere Budget-Monate — Basis für die Trends & Insights-Seite:
    Einnahmen/Ausgaben pro Monat, Ausgaben-Verlauf pro Umschlag, Top-Ausgaben-Umschläge
    und ein Jahresvergleich für den aktuellsten Monat im Zeitraum."""

    def get(self, request):
        try:
            months_count = int(request.query_params.get("months", 12))
        except (TypeError, ValueError):
            months_count = 12
        months_count = max(1, min(months_count, 24))

        start_day = get_month_start_day()
        anchor_year, anchor_month = budget_period_for_date(date.today(), start_day)

        periods = []
        y, m = anchor_year, anchor_month
        for _ in range(months_count):
            periods.append((y, m))
            y, m = (y - 1, 12) if m == 1 else (y, m - 1)
        periods.reverse()

        months_payload = []
        income_by_month = []
        expense_by_month = []
        net_by_month = []
        for py, pm in periods:
            start, end = budget_period_bounds(py, pm, start_day)
            income = Transaction.objects.filter(
                date__gte=start, date__lte=end, amount__gt=0, transfer_pair__isnull=True
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
            expense = -(
                Transaction.objects.filter(
                    date__gte=start, date__lte=end, amount__lt=0, transfer_pair__isnull=True
                ).aggregate(total=Sum("amount"))["total"]
                or Decimal("0")
            )
            months_payload.append({"year": py, "month": pm})
            income_by_month.append(str(income))
            expense_by_month.append(str(expense))
            net_by_month.append(str(income - expense))

        categories = Category.objects.filter(is_archived=False).exclude(kind=Category.Kind.INCOME)
        category_payload = []
        totals = {}
        for c in categories:
            spent_series = [c.spent_in_month(py, pm) for py, pm in periods]
            totals[c.id] = sum(spent_series, Decimal("0"))
            category_payload.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "kind": c.kind,
                    "color": c.color,
                    "icon": c.icon,
                    "spent_by_month": [str(v) for v in spent_series],
                }
            )

        top_categories = sorted(
            (c for c in category_payload if totals[c["id"]] > 0),
            key=lambda c: totals[c["id"]],
            reverse=True,
        )[:5]
        top_categories = [
            {"id": c["id"], "name": c["name"], "color": c["color"], "total_spent": str(totals[c["id"]])}
            for c in top_categories
        ]

        previous_year = anchor_year - 1
        prev_start, prev_end = budget_period_bounds(previous_year, anchor_month, start_day)
        previous_income = Transaction.objects.filter(
            date__gte=prev_start, date__lte=prev_end, amount__gt=0, transfer_pair__isnull=True
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        previous_expense = -(
            Transaction.objects.filter(
                date__gte=prev_start, date__lte=prev_end, amount__lt=0, transfer_pair__isnull=True
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0")
        )

        return Response(
            {
                "months": months_payload,
                "income_by_month": income_by_month,
                "expense_by_month": expense_by_month,
                "net_by_month": net_by_month,
                "categories": category_payload,
                "top_categories": top_categories,
                "year_over_year": {
                    "current_year": anchor_year,
                    "current_month": anchor_month,
                    "current_income": income_by_month[-1],
                    "current_expense": expense_by_month[-1],
                    "previous_year": previous_year,
                    "previous_income": str(previous_income),
                    "previous_expense": str(previous_expense),
                },
            }
        )
