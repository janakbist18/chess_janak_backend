"""
Fast and optimized authentication service
"""
from django.contrib.auth import authenticate
from django.db.models import Prefetch
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User, UserProfile


def get_user_with_profile(email: str = None, username: str = None) -> User:
    """Get user with prefetched profile in a single query"""
    query = User.objects.select_related("profile").prefetch_related("email_otps")

    if email:
        return query.filter(email__iexact=email).first()
    elif username:
        return query.filter(username__iexact=username).first()

    return None


def generate_tokens_for_user(user: User) -> dict:
    """Fast token generation"""
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


def authenticate_user(email_or_username: str, password: str) -> User:
    """Fast user authentication with profile prefetch"""
    # Check if it's an email or username
    if "@" in email_or_username:
        user = get_user_with_profile(email=email_or_username)
        if user and user.check_password(password):
            return user
    else:
        user = get_user_with_profile(username=email_or_username)
        if user and user.check_password(password):
            return user

    return None


def user_exists(email: str = None, username: str = None) -> bool:
    """Fast user existence check"""
    if email:
        return User.objects.filter(email__iexact=email).exists()
    elif username:
        return User.objects.filter(username__iexact=username).exists()
    return False
