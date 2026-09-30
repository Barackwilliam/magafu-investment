from django.core.management.base import BaseCommand

from loans.services import apply_daily_penalties


class Command(BaseCommand):
    help = "Weka faini ya siku kwa mikopo iliyo nje ya mkataba. Endesha mara moja kila siku (cron)."

    def handle(self, *args, **opts):
        n = apply_daily_penalties()
        self.stdout.write(self.style.SUCCESS(f"Faini {n} zimewekwa."))
