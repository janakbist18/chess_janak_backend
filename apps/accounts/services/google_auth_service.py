import requests
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


def verify_google_access_token(access_token: str) -> dict:
    """
    Verify Google access token by fetching user info from Google API
    """
    try:
        response = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5
        )
        response.raise_for_status()
        user_info = response.json()

        # Verify we have email
        if not user_info.get("email"):
            raise ValueError("Google account did not return an email address")

        # Ensure name field exists (use email prefix if not provided)
        if not user_info.get("name"):
            user_info["name"] = user_info.get("email", "").split("@")[0]

        # Map verified_email to email_verified for consistency with ID token format
        if "verified_email" in user_info and "email_verified" not in user_info:
            user_info["email_verified"] = user_info.get("verified_email", False)

        return user_info
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to verify Google access token: {str(e)}")


def handle_google_login(id_token_value: str) -> dict:
    google_data = verify_google_id_token(id_token_value)
    user = get_or_create_google_user(google_data)
    tokens = generate_tokens_for_user(user)
    return {
        "user": user,
        "tokens": tokens,
    }


def handle_google_login_with_access_token(access_token: str) -> dict:
    """
    Handle Google login using access token instead of ID token
    """
    google_data = verify_google_access_token(access_token)
    user = get_or_create_google_user(google_data)
    tokens = generate_tokens_for_user(user)
    return {
        "user": user,
        "tokens": tokens,
    }