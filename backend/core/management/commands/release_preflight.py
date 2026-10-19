from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.core.management import call_command
from billing.models import Subscription

class Command(BaseCommand):
    help = "Read-only production blockers inspection. Does not mutate database."

    def handle(self, *args, **kwargs):
        failures=[]
        if settings.DEBUG:
            failures.append("DEBUG must be disabled")
        if connection.vendor != "postgresql":
            failures.append("PostgreSQL required")
        if not settings.SESSION_COOKIE_SECURE or not settings.CSRF_COOKIE_SECURE:
            failures.append("Secure cookies required")
        if not settings.SECURE_SSL_REDIRECT:
            failures.append("HTTPS redirect required")
        if settings.ALLOW_PUBLIC_UNVERIFIED_REGISTRATION:
            failures.append("Unverified registration must remain disabled")
        # S12 is still incomplete: do not allow sign-off by merely configuring plans.
        failures.append("S12 subscription write enforcement is not implemented")
        failures.append("Verified PSP/fiscal integration and restore drill not completed")
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            failures.append("Database connectivity check failed")
        for item in failures:
            self.stderr.write("BLOCKER: "+item)
        if failures:
            raise CommandError("Commercial release blocked. "+str(len(failures))+" issue(s).")
        self.stdout.write(self.style.SUCCESS("Preflight passed"))
