import calendar
from datetime import date
from decimal import Decimal

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Sum
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Account, Category, RecurringTransaction, Transaction
from .serializers import (
    AccountSerializer,
    CategorySerializer,
    LoginSerializer,
    RecurringTransactionSerializer,
    SignupSerializer,
    TransactionSerializer,
    UserSerializer,
)
from .services import generate_due_recurring


def _month_bounds(year, month):
    first = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1
    return first, last_day, (prev_year, prev_month), (next_year, next_month)


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
        if params.get("year") and params.get("month"):
            qs = qs.filter(date__year=params["year"], date__month=params["month"])
        if params.get("category"):
            qs = qs.filter(category_id=params["category"])
        if params.get("account"):
            qs = qs.filter(account_id=params["account"])
        return qs


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

        year, month = _requested_year_month(request)
        first, days_in_month, (prev_year, prev_month), (next_year, next_month) = _month_bounds(year, month)

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

        income_total = Transaction.objects.filter(
            date__year=year, date__month=month, amount__gt=0
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        expense_total = -(
            Transaction.objects.filter(date__year=year, date__month=month, amount__lt=0).aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0")
        )

        from debts.models import Debt

        open_debts = Debt.objects.filter(is_paid_off=False)
        total_debt = sum((d.current_balance for d in open_debts), Decimal("0"))
        total_minimum = sum((d.minimum_payment for d in open_debts), Decimal("0"))

        recent_transactions = Transaction.objects.select_related("account", "category")[:8]

        return Response(
            {
                "year": year,
                "month": month,
                "month_name": first.strftime("%B %Y"),
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
            }
        )
