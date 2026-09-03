from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Account, Category, Transaction
from core.serializers import TransactionSerializer

from .camt053 import Camt053ParseError, parse_camt053, suggest_category
from .models import ImportBatch
from .serializers import ImportBatchSerializer


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
        existing_refs = set(
            Transaction.objects.filter(account=account, import_ref__isnull=False).values_list(
                "import_ref", flat=True
            )
        )

        rows = []
        for row in parsed:
            suggestion = suggest_category(row["description"], row["counterparty"], categories)
            rows.append(
                {
                    **_serialize_row(row),
                    "suggested_category_id": suggestion.id if suggestion else None,
                    "is_duplicate": row["entry_ref"] in existing_refs,
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
            if not row.get("include"):
                continue
            if row.get("is_duplicate"):
                skipped += 1
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
