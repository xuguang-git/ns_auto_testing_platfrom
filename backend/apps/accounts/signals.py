from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def initialize_rbac(sender, **kwargs):
    if sender.name != "apps.accounts":
        return
    from apps.accounts.services import bootstrap_superuser_profile

    bootstrap_superuser_profile()
