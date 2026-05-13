from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Django app configuration for account registration/profile hooks."""

    name = 'accounts'

    def ready(self):
        """Import signal receivers when Django starts the app registry."""
        import accounts.signals  # noqa: F401
