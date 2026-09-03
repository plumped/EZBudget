from datetime import date

from .models import RecurringTransaction, Transaction


def generate_due_recurring(today=None):
    """Erzeugt Buchungen für alle aktiven wiederkehrenden Vorlagen, deren Tag
    im aktuellen Monat bereits erreicht ist und die für diesen Monat noch
    keine Buchung haben. Wiederholtes Aufrufen im selben Monat ist sicher
    (Duplikaterkennung über import_ref).
    """
    today = today or date.today()
    created = []
    due = RecurringTransaction.objects.filter(is_active=True, day_of_month__lte=today.day)
    for rt in due:
        ref = rt.import_ref_for(today.year, today.month)
        if Transaction.objects.filter(import_ref=ref).exists():
            continue
        txn = Transaction.objects.create(
            account=rt.account,
            category=rt.category,
            date=date(today.year, today.month, rt.day_of_month),
            amount=rt.amount,
            description=rt.description,
            counterparty=rt.counterparty,
            import_ref=ref,
        )
        created.append(txn)
    return created
