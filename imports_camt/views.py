from datetime import date, datetime
from decimal import Decimal

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.models import Account, Category, Transaction

from .camt053 import Camt053ParseError, parse_camt053, suggest_category
from .models import ImportBatch

SESSION_KEY = "camt_import_preview"


def _serialize(rows):
    """Für die Session JSON-tauglich machen (Decimal/date -> str)."""
    out = []
    for r in rows:
        out.append(
            {
                **r,
                "date": r["date"].isoformat() if r["date"] else "",
                "amount": str(r["amount"]),
            }
        )
    return out


def _deserialize(rows):
    out = []
    for r in rows:
        out.append(
            {
                **r,
                "date": datetime.fromisoformat(r["date"]).date() if r["date"] else None,
                "amount": Decimal(r["amount"]),
            }
        )
    return out


def import_upload(request):
    accounts = Account.objects.filter(is_archived=False)

    if request.method == "POST":
        account = get_object_or_404(Account, pk=request.POST.get("account"))
        file = request.FILES.get("camt_file")
        if not file:
            messages.error(request, "Bitte eine CAMT.053-XML-Datei auswählen.")
            return redirect("imports:import_upload")

        try:
            parsed = parse_camt053(file)
        except Camt053ParseError as exc:
            messages.error(request, f"Import fehlgeschlagen: {exc}")
            return redirect("imports:import_upload")

        if not parsed:
            messages.warning(request, "Keine Buchungen in der Datei gefunden.")
            return redirect("imports:import_upload")

        categories = list(Category.objects.filter(is_archived=False))
        existing_refs = set(
            Transaction.objects.filter(account=account, import_ref__isnull=False).values_list(
                "import_ref", flat=True
            )
        )

        for row in parsed:
            suggestion = suggest_category(row["description"], row["counterparty"], categories)
            row["suggested_category_id"] = suggestion.id if suggestion else None
            row["is_duplicate"] = row["entry_ref"] in existing_refs

        request.session[SESSION_KEY] = {
            "account_id": account.id,
            "filename": file.name,
            "rows": _serialize(parsed),
        }
        return redirect("imports:import_preview")

    return render(request, "imports_camt/upload.html", {"accounts": accounts})


def import_preview(request):
    data = request.session.get(SESSION_KEY)
    if not data:
        messages.info(request, "Keine Import-Vorschau vorhanden. Bitte zuerst eine Datei hochladen.")
        return redirect("imports:import_upload")

    account = get_object_or_404(Account, pk=data["account_id"])
    rows = _deserialize(data["rows"])
    categories = Category.objects.filter(is_archived=False)

    if request.method == "POST":
        created, skipped = 0, 0
        for idx, row in enumerate(rows):
            field = f"include_{idx}"
            if field not in request.POST:
                continue
            if row["is_duplicate"]:
                skipped += 1
                continue
            category_id = request.POST.get(f"category_{idx}") or None
            Transaction.objects.create(
                account=account,
                category_id=category_id,
                date=row["date"] or date.today(),
                amount=row["amount"],
                description=row["description"],
                counterparty=row["counterparty"],
                import_ref=row["entry_ref"],
            )
            created += 1

        ImportBatch.objects.create(
            account=account,
            filename=data["filename"],
            transactions_created=created,
            transactions_skipped=skipped,
        )
        del request.session[SESSION_KEY]
        messages.success(request, f"Import abgeschlossen: {created} Buchungen importiert, {skipped} übersprungen.")
        return redirect("core:transaction_list")

    context = {
        "account": account,
        "filename": data["filename"],
        "rows": list(enumerate(rows)),
        "categories": categories,
    }
    return render(request, "imports_camt/preview.html", context)


def import_cancel(request):
    request.session.pop(SESSION_KEY, None)
    return redirect("imports:import_upload")


def import_history(request):
    batches = ImportBatch.objects.select_related("account")
    return render(request, "imports_camt/history.html", {"batches": batches})
