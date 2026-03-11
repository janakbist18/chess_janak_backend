from django.apps import AppConfig


class ChessplayConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.chessplay"
    label = "chessplay"

    def ready(self):
        import apps.chessplay.signals  # noqa