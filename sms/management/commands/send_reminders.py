from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from loans.models import Loan
from sms.services import send_reminder


class Command(BaseCommand):
    help = "Tuma vikumbusho kwa wanaopaswa kumaliza kesho na leo. Endesha kila asubuhi (cron)."

    def handle(self, *args, **opts):
        today = timezone.localdate()
        loans = (Loan.objects.active()
                 .filter(due_date__in=[today, today + timedelta(days=1)])
                 .select_related("customer"))
        n = 0
        for loan in loans:
            if loan.balance > 0:
                send_reminder(loan)
                n += 1
        self.stdout.write(self.style.SUCCESS(f"Vikumbusho {n} vimeshughulikiwa."))
