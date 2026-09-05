from django.core.management.base import BaseCommand

from debts.services import accrue_monthly_interest


class Command(BaseCommand):
    help = "Bucht den fälligen Monatszins auf offene Schulden (echt auf current_balance, nicht nur simuliert)."

    def handle(self, *args, **options):
        accrued = accrue_monthly_interest()
        if accrued:
            names = ", ".join(d.name for d in accrued)
            self.stdout.write(self.style.SUCCESS(f"Zins gebucht für: {names}"))
        else:
            self.stdout.write("Kein fälliger Zins zu buchen.")
