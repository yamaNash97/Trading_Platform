from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Django app setup for signup and profile hooks."""

    name = 'accounts'

    def ready(self):
        """Import signal receivers when Django starts the app."""
        import accounts.signals  # noqa: F401
