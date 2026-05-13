from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    """Create a Profile row for each newly created auth user."""
    if created:
        # get_or_create keeps the signal idempotent if another setup path has
        # already created the related profile.
        Profile.objects.get_or_create(user=instance)
