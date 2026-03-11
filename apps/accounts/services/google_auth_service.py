from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from apps.accounts.models import User
from apps.accounts.services.auth_service import generate_tokens_for_user


def verify_google_id_token(token: str) -> dict:
    audience_candidates = [
        settings.GOOGLE_WEB_CLIENT_ID,
        settings.GOOGLE_ANDROID_CLIENT_ID,
        settings.GOOGLE_IOS_CLIENT_ID,
    ]
    audience_candidates = [item for item in audience_candidates if item]

    last_error = None
    for audience in audience_candidates:
        try:
            info = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                audience,
            )
            return info
        except Exception as exc:
            last_error = exc

    if last_error:
        raise last_error

    raise ValueError("Google client IDs are not configured.")


def get_or_create_google_user(google_data: dict) -> User:
    email = google_data.get("email")
    name = google_data.get("name") or email.split("@")[0]
    email_verified = google_data.get("email_verified", False)

    if not email:
        raise ValueError("Google account did not return an email address.")

    user = User.objects.filter(email__iexact=email).first()

    if user:
        if not user.is_google_account:
            user.is_google_account = True
        if email_verified:
            user.is_verified = True
            user.is_active = True
        if not user.name:
            user.name = name
        user.save()
        return user

    base_username = email.split("@")[0].replace(" ", "").lower()
    username = base_username
    counter = 1

    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1

    user = User.objects.create_user(
        email=email,
        username=username,
        name=name,
        password=None,
        is_google_account=True,
        is_verified=bool(email_verified),
        is_active=bool(email_verified),
    )
    user.set_unusable_password()
    user.save()
    return user


def handle_google_login(id_token_value: str) -> dict:
    google_data = verify_google_id_token(id_token_value)
    user = get_or_create_google_user(google_data)
    tokens = generate_tokens_for_user(user)
    return {
        "user": user,
        "tokens": tokens,
    }