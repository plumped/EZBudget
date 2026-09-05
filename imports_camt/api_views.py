from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Account, Category, Transaction
from core.serializers import TransactionSerializer

from .camt053 import Camt053ParseError, parse_camt053, suggest_category
from .models import ImportBatch, Rule
from .serializers import ImportBatchSerializer, RuleApplySerializer, RuleConditionSerializer, RuleSerializer

PREVIEW_LIMIT = 50


def _apply_text_lookup(qs, field, match_type, value):
    if match_type == Rule.MatchType.STARTSWITH:
        return qs.filter(**{f"{field}__istartswith": value})
    if match_type == Rule.MatchType.EXACT:
        return qs.filter(**{f"{field}__iexact": value})
    return qs.filter(**{f"{field}__icontains": value})


def _filter_transactions(qs, data):
    if data.get("description_value"):
        qs = _apply_text_lookup(qs, "description", data["description_match_type"], data["description_value"])
    if data.get("counterparty_value"):
        qs = _apply_text_lookup(qs, "counterparty", data["counterparty_match_type"], data["counterparty_value"])
    if data.get("amount_min") is not None:
        qs = qs.filter(amount__gte=data["amount_min"])
    if data.get("amount_max") is not None:
        qs = qs.filter(amount__lte=data["amount_max"])
    return qs


class RuleViewSet(viewsets.ModelViewSet):
    queryset = Rule.objects.select_related("category")
    serializer_class = RuleSerializer

    @action(detail=False, methods=["post"])
    def preview(self, request):
        """Welche bestehenden Buchungen passen zu den gerade eingegebenen
        (noch nicht zwingend gespeicherten) Bedingungen — vor dem Anwenden."""
        serializer = RuleConditionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        qs = _filter_transactions(
            Transaction.objects.select_related("account", "category").order_by("-date", "-id"),
            serializer.validated_data,
        )
        count = qs.count()
        rows = TransactionSerializer(qs[:PREVIEW_LIMIT], many=True).data
        return Response({"count": count, "transactions": rows, "preview_limit": PREVIEW_LIMIT})

    @action(detail=False, methods=["post"])
    def apply(self, request):
        """Ordnet allen aktuell passenden bestehenden Buchungen den angegebenen
        Umschlag zu (löst dabei ganz normal Transaction.save() pro Buchung aus,
        z.B. für die Schuld-Saldo-Synchronisation)."""
        serializer = RuleApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        category = data.pop("category")
        qs = _filter_transactions(Transaction.objects.all(), data)
        updated = 0
        for txn in qs:
            txn.category = category
            txn.save(update_fields=["category"])
            updated += 1
        return Response({"updated": updated})


def _suggest_category(description, counterparty, amount, categories, rules):
    for rule in rules:
        if rule.matches(description, counterparty, amount):
            return rule.category
    return suggest_category(description, counterparty, categories)


def _serialize_row(row):
    return {
        **row,
        "date": row["date"].isoformat() if row["date"] else None,
        "amount": str(row["amount"]),
    }


class ImportParseView(APIView):
    """Parst eine hochgeladene CAMT.053-Datei zustandslos und liefert eine
    Vorschau inkl. Auto-Zuordnungsvorschlag und Duplikat-Markierung zurück.
    Es wird noch nichts in der Datenbank gespeichert."""

    def post(self, request):
        account_id = request.data.get("account")
        if not account_id:
            return Response({"detail": "Konto ist erforderlich."}, status=status.HTTP_400_BAD_REQUEST)
        account = Account.objects.filter(pk=account_id).first()
        if account is None:
            return Response({"detail": "Konto nicht gefunden."}, status=status.HTTP_404_NOT_FOUND)

        file = request.FILES.get("camt_file")
        if not file:
            return Response({"detail": "Bitte eine CAMT.053-XML-Datei auswählen."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            parsed = parse_camt053(file)
        except Camt053ParseError as exc:
            return Response({"detail": f"Import fehlgeschlagen: {exc}"}, status=status.HTTP_400_BAD_REQUEST)

        if not parsed:
            return Response({"detail": "Keine Buchungen in der Datei gefunden.", "rows": []})

        categories = list(Category.objects.filter(is_archived=False))
        rules = list(Rule.objects.filter(is_active=True, category__is_archived=False).select_related("category"))
        existing_refs = set(
            Transaction.objects.filter(account=account, import_ref__isnull=False).values_list(
                "import_ref", flat=True
            )
        )
        # Weiche Duplikat-Erkennung für Buchungen OHNE Bank-Referenz — z.B. eine
        # Zahlung, die vorher schon manuell erfasst wurde (etwa über "Zahlung
        # erfassen" beim Schulden-Sweep-Vorschlag) und jetzt zusätzlich importiert
        # wird: die harte Referenz-Prüfung oben greift dafür nicht, weil eine manuell
        # erfasste Buchung nie eine import_ref hat. Nur ein Hinweis, kein Blocker
        # (siehe is_possible_duplicate unten) — als Multiset, damit zwei zufällig
        # gleich hohe, aber unabhängige Buchungen am selben Tag nicht beide verloren
        # gehen, sondern nur so viele wie tatsächlich schon vorhandene Buchungen mit
        # exakt diesem Datum/Betrag existieren.
        existing_by_date_amount = Counter(
            Transaction.objects.filter(account=account, import_ref__isnull=True).values_list("date", "amount")
        )

        rows = []
        for row in parsed:
            suggestion = _suggest_category(row["description"], row["counterparty"], row["amount"], categories, rules)
            is_duplicate = row["entry_ref"] in existing_refs
            is_possible_duplicate = False
            if not is_duplicate:
                key = (row["date"], row["amount"])
                if existing_by_date_amount.get(key, 0) > 0:
                    is_possible_duplicate = True
                    existing_by_date_amount[key] -= 1
            rows.append(
                {
                    **_serialize_row(row),
                    "suggested_category_id": suggestion.id if suggestion else None,
                    "is_duplicate": is_duplicate,
                    "is_possible_duplicate": is_possible_duplicate,
                }
            )

        return Response({"account": account.id, "filename": file.name, "rows": rows})


class ImportConfirmView(APIView):
    def post(self, request):
        account_id = request.data.get("account")
        account = Account.objects.filter(pk=account_id).first()
        if account is None:
            return Response({"detail": "Konto nicht gefunden."}, status=status.HTTP_404_NOT_FOUND)

        filename = request.data.get("filename", "")
        rows = request.data.get("rows", [])

        created, skipped = 0, 0
        for row in rows:
            # Duplikat-Zeilen zählen als übersprungen, auch wenn das Frontend ihre
            # Checkbox deaktiviert und "include" daher nie true sendet — sonst
            # bräche die include-Prüfung unten schon vorher ab und skipped bliebe 0.
            if row.get("is_duplicate"):
                skipped += 1
                continue
            if not row.get("include"):
                continue
            try:
                amount = Decimal(str(row["amount"]))
            except (InvalidOperation, KeyError):
                continue
            row_date = row.get("date")
            try:
                txn_date = datetime.fromisoformat(row_date).date() if row_date else date.today()
            except ValueError:
                txn_date = date.today()

            Transaction.objects.create(
                account=account,
                category_id=row.get("category_id") or None,
                date=txn_date,
                amount=amount,
                description=row.get("description", ""),
                counterparty=row.get("counterparty", ""),
                import_ref=row.get("entry_ref"),
            )
            created += 1

        batch = ImportBatch.objects.create(
            account=account,
            filename=filename,
            transactions_created=created,
            transactions_skipped=skipped,
        )

        return Response(
            {
                "created": created,
                "skipped": skipped,
                "batch": ImportBatchSerializer(batch).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ImportHistoryView(APIView):
    def get(self, request):
        batches = ImportBatch.objects.select_related("account")
        return Response(ImportBatchSerializer(batches, many=True).data)
