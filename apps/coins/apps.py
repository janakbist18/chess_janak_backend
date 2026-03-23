"""
Django app configuration for coin system.
Registers models, signals, and app-specific settings.
"""
from django.apps import AppConfig


class CoinsConfig(AppConfig):
    """Configuration for coins app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.coins'
    verbose_name = 'Coin System'

    def ready(self):
        """Initialize app - register signals."""
        import apps.coins.signals  # noqa
