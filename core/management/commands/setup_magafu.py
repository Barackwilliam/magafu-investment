from django.core.management.base import BaseCommand

from core.models import Branch
from loans.models import LoanProduct


class Command(BaseCommand):
    help = "Inaweka tawi la kwanza na aina ya mkopo ya mfano kama hazipo. Salama kuendesha mara nyingi."

    def handle(self, *args, **opts):
        if not Branch.objects.exists():
            Branch.objects.create(name="Makao Makuu")
            self.stdout.write("Tawi 'Makao Makuu' limeundwa.")
        if not LoanProduct.objects.exists():
            LoanProduct.objects.create(name="Mkopo wa siku 30", interest_rate=20, duration_days=30,
                                       repayment_frequency="DAILY", form_fee=10000)
            self.stdout.write("Aina ya mkopo ya mfano imeundwa (badilisha kwenye Mipangilio).")
        self.stdout.write(self.style.SUCCESS("Tayari."))
