from django.conf import settings


def build_room_invite_link(invite_code: str) -> str:
    app_base_url = getattr(settings, "APP_BASE_URL", "http://127.0.0.1:8000")
    app_base_url = app_base_url.rstrip("/")
    return f"{app_base_url}/join/{invite_code}"