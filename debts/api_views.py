from datetime import date
from decimal import Decimal, InvalidOperation

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Transaction
from core.serializers import TransactionSerializer

from .models import Debt
from .serializers import DebtSerializer
from .services import simulate_payoff


class DebtViewSet(viewsets.ModelViewSet):
    queryset = Debt.objects.all()
    serializer_class = DebtSerializer

    def get_queryset(self):
        qs = Debt.objects.all()
        if self.request.query_params.get("open_only") == "1":
            qs = qs.filter(is_paid_off=False)
        return qs

    @action(detail=True, methods=["get", "post"])
    def payments(self, request, pk=None):
        """Zahlungshistorie einer Schuld = Buchungen auf ihrem verknüpften Umschlag.

        Eine Zahlung hier ist eine Kurzform für "Buchung mit diesem Umschlag
        erfassen": sie legt eine normale Transaction an (verringert also auch
        den Kontostand), statt eine separate, unverknüpfte Zahlungstabelle zu
        pflegen — Transaction.save() reduziert current_balance automatisch.
        """
        debt = self.get_object()
        if request.method == "POST":
            if debt.category_id is None:
                return Response({"detail": "Schuld hat keinen verknüpften Umschlag."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                paid_amount = Decimal(str(request.data.get("amount", "0")).replace(",", "."))
            except InvalidOperation:
                return Response({"amount": ["Ungültiger Betrag."]}, status=status.HTTP_400_BAD_REQUEST)
            payload = {
                "account": request.data.get("account"),
                "category": debt.category_id,
                "date": request.data.get("date"),
                "amount": str(-abs(paid_amount)),
                "description": request.data.get("note") or f"Tilgung: {debt.name}",
                "counterparty": debt.creditor,
            }
            serializer = TransactionSerializer(data=payload)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            debt.refresh_from_db()
            return Response(
                {"debt": DebtSerializer(debt).data, "transaction": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        if debt.category_id is None:
            return Response([])
        transactions = Transaction.objects.filter(category_id=debt.category_id).order_by("-date", "-id")
        return Response(TransactionSerializer(transactions, many=True).data)


class PayoffSimulationView(APIView):
    def get(self, request):
        strategy = request.query_params.get("strategy", "avalanche")
        if strategy not in ("avalanche", "snowball"):
            strategy = "avalanche"
        try:
            extra_budget = Decimal(str(request.query_params.get("extra", "0")).replace(",", "."))
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
        result = simulate_payoff(debt_dicts, strategy=strategy, extra_budget=extra_budget, start_date=date.today())

        return Response(
            {
                "strategy": strategy,
                "extra_budget": str(extra_budget),
                "total_balance": str(total_balance),
                "total_minimum": str(total_minimum),
                "total_monthly": str(total_minimum + extra_budget),
                "months": result.months,
                "total_interest": str(result.total_interest.quantize(Decimal("0.01"))),
                "payoff_order": result.payoff_order,
                "debt_free_date": result.debt_free_date,
                "reached_max": result.reached_max,
                "schedule": [
                    {
                        "month": row["month"],
                        "date": row["date"],
                        "total_balance": str(row["total_balance"].quantize(Decimal("0.01"))),
                    }
                    for row in result.schedule
                ],
            }
        )
