from django.core.management.base import BaseCommand
from ninepsb.services import fetch_and_update_psb_banks

class Command(BaseCommand):
    help = "Fetch and update 9PSB bank list"

    def handle(self, *args, **kwargs):
        try:
            message = fetch_and_update_psb_banks()
            self.stdout.write(self.style.SUCCESS(message))
        except Exception as e:
            self.stderr.write(self.style.ERROR(str(e)))
