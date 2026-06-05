from django.core.management.base import BaseCommand

from apps.accounts.services import bootstrap_superuser_profile, ensure_builtin_roles


class Command(BaseCommand):
    help = "Initialize RBAC permissions and built-in roles."

    def handle(self, *args, **options):
        ensure_builtin_roles()
        bootstrap_superuser_profile()
        self.stdout.write(self.style.SUCCESS("RBAC permissions and built-in roles initialized."))
