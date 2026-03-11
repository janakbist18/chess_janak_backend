from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


def get_now():
    return timezone.now()


def get_user_by_email_or_username(email_or_username: str):
    value = email_or_username.strip()
    if "@" in value:
        return User.objects.filter(email__iexact=value).first()
    return User.objects.filter(username__iexact=value).first()