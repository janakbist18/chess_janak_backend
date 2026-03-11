from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User


def generate_tokens_for_user(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


def authenticate_user_by_email_or_username(email_or_username: str, password: str):
    if "@" in email_or_username:
        user = User.objects.filter(email__iexact=email_or_username.strip()).first()
        if not user:
            return None
        return authenticate(username=user.email, password=password)

    user = User.objects.filter(username__iexact=email_or_username.strip()).first()
    if not user:
        return None
    return authenticate(username=user.email, password=password)