from datetime import date

from .models import RecurringTransaction, Transaction


def generate_due_recurring(today=None):
    """Erzeugt Buchungen für alle aktiven wiederkehrenden Vorlagen, deren Periode
    (Woche/2 Wochen/Monat/Jahr, je nach `frequency`) am heutigen Tag bereits fällig
    ist und die für diese Periode noch keine Buchung haben. Wiederholtes Aufrufen
    in derselben Periode ist sicher (Duplikaterkennung über import_ref).
    """
    today = today or date.today()
    created = []
    due = RecurringTransaction.objects.filter(is_active=True)
    for rt in due:
        if not rt.is_due_on(today):
            continue
        ref = rt.import_ref_for(today)
        if Transaction.objects.filter(import_ref=ref).exists():
            continue
        txn = Transaction.objects.create(
            account=rt.account,
            category=rt.category,
            date=rt.occurrence_date(today),
            amount=rt.amount,
            description=rt.description,
            counterparty=rt.counterparty,
            import_ref=ref,
        )
        created.append(txn)
    return created
