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
from .services import allocate_extra_once, eligible_envelope_surplus, simulate_payoff


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
        """Zahlungshistorie einer Schuld.

        Ohne Kontoverknüpfung (klassische Schuld): Buchungen auf ihrem verknüpften
        Umschlag. Eine Zahlung hier ist eine Kurzform für "Buchung mit diesem Umschlag
        erfassen": sie legt eine normale Transaction an (verringert also auch den
        Kontostand), statt eine separate, unverknüpfte Zahlungstabelle zu pflegen —
        Transaction.save() reduziert current_balance automatisch.

        Mit Kontoverknüpfung (z.B. Kreditkarte, siehe Debt.account): die komplette
        Buchungshistorie dieses Kontos — Ausgaben und Zahlungen laufen dort ganz normal
        (mit echten Umschlägen kategorisiert bzw. per Transfer), die Restschuld folgt
        automatisch. Der manuelle Zahlungs-Kurzweg ist dafür gesperrt, um doppelte
        Buchungswege zu vermeiden — Zahlungen laufen hier über einen normalen Transfer.
        """
        debt = self.get_object()
        if request.method == "POST":
            if debt.account_id is not None:
                return Response(
                    {
                        "detail": (
                            "Diese Schuld ist mit einem Konto verknüpft — Zahlungen laufen über "
                            "einen normalen Transfer auf dieses Konto, nicht über diesen Weg."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
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
        if debt.account_id is not None:
            transactions = Transaction.objects.filter(account_id=debt.account_id).order_by("-date", "-id")
            return Response(TransactionSerializer(transactions, many=True).data)
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
                "max_extra": d.max_extra_payment,
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
                "unallocated_extra": str(result.unallocated_extra.quantize(Decimal("0.01"))),
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


class SweepProposalView(APIView):
    """Monatsende-Vorschlag: wie viel ungenutztes Umschlag-Budget könnte diesen
    Monat zusätzlich zur Schuldentilgung verwendet werden, und wie würde sich das
    nach der gewählten Strategie auf die offenen Schulden verteilen?

    Löst KEINE echte Überweisung aus — die App bildet Buchungen nur ab, eine
    tatsächliche Zahlung macht der Nutzer selbst bei seiner Bank und trägt sie
    danach ganz normal über den bestehenden Zahlungsweg ein.
    """

    def get(self, request):
        from core.budget_month import budget_period_for_date, get_month_start_day

        strategy = request.query_params.get("strategy", "avalanche")
        if strategy not in ("avalanche", "snowball"):
            strategy = "avalanche"

        year, month = budget_period_for_date(date.today(), get_month_start_day())
        total_available, sources = eligible_envelope_surplus(year, month)

        debts = Debt.objects.filter(is_paid_off=False)
        debt_dicts = [
            {
                "id": d.id,
                "name": d.name,
                "balance": d.current_balance,
                "rate": d.interest_rate,
                "max_extra": d.max_extra_payment,
            }
            for d in debts
        ]
        result = allocate_extra_once(debt_dicts, strategy=strategy, extra_budget=total_available)

        return Response(
            {
                "strategy": strategy,
                "total_available": str(total_available.quantize(Decimal("0.01"))),
                "sources": [
                    {"id": s["id"], "name": s["name"], "amount": str(s["amount"].quantize(Decimal("0.01")))}
                    for s in sources
                ],
                "allocations": [
                    {"id": a["id"], "name": a["name"], "amount": str(a["amount"].quantize(Decimal("0.01")))}
                    for a in result.allocations
                ],
                "unallocated": str(result.unallocated.quantize(Decimal("0.01"))),
            }
        )
