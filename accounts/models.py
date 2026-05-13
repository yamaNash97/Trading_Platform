from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Small user profile linked one-to-one with Django's auth user.

    The app currently stores an optional display name and creation timestamp.
    Profiles are created automatically by ``accounts.signals.create_profile``
    whenever a new user is saved.
    """

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Use the display name when set, otherwise fall back to username."""
        return self.display_name or self.user.get_username()
