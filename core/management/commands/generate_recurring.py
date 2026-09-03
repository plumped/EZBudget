from django.core.management.base import BaseCommand

from core.services import generate_due_recurring


class Command(BaseCommand):
    help = "Generiert fällige wiederkehrende Buchungen (Fixkosten, Abos, Lohn ...) für den aktuellen Monat."

    def handle(self, *args, **options):
        created = generate_due_recurring()
        if created:
            self.stdout.write(self.style.SUCCESS(f"{len(created)} Buchung(en) generiert."))
        else:
            self.stdout.write("Keine fälligen wiederkehrenden Buchungen.")
