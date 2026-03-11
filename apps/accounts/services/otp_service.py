from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.accounts.models import EmailOTP, PasswordResetOTP, User
from apps.accounts.services.email_service import (
    send_password_reset_otp_email,
    send_registration_otp_email,
)
from apps.core.utils import generate_numeric_otp


def invalidate_old_email_otps(user: User, purpose: str) -> None:
    EmailOTP.objects.filter(
        user=user,
        purpose=purpose,
        is_used=False,
    ).update(is_used=True)


def invalidate_old_password_reset_otps(user: User) -> None:
    PasswordResetOTP.objects.filter(
        user=user,
        is_used=False,
    ).update(is_used=True)


def create_email_verification_otp(user: User, purpose: str = "registration") -> EmailOTP:
    invalidate_old_email_otps(user, purpose)

    otp_code = generate_numeric_otp(6)
    expires_at = timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

    otp = EmailOTP.objects.create(
        user=user,
        email=user.email,
        otp_code=otp_code,
        purpose=purpose,
        expires_at=expires_at,
    )

    send_registration_otp_email(
        name=user.name,
        email=user.email,
        otp_code=otp_code,
    )
    return otp


def create_password_reset_otp(user: User) -> PasswordResetOTP:
    invalidate_old_password_reset_otps(user)

    otp_code = generate_numeric_otp(6)
    expires_at = timezone.now() + timedelta(
        minutes=settings.PASSWORD_RESET_OTP_EXPIRY_MINUTES
    )

    otp = PasswordResetOTP.objects.create(
        user=user,
        email=user.email,
        otp_code=otp_code,
        expires_at=expires_at,
    )

    send_password_reset_otp_email(
        name=user.name,
        email=user.email,
        otp_code=otp_code,
    )
    return otp


def get_valid_email_otp(user: User, otp_code: str, purpose: str) -> EmailOTP | None:
    otp = (
        EmailOTP.objects.filter(
            user=user,
            otp_code=otp_code,
            purpose=purpose,
            is_used=False,
        )
        .order_by("-created_at")
        .first()
    )

    if not otp:
        return None

    if otp.is_expired:
        return None

    return otp


def get_valid_password_reset_otp(user: User, otp_code: str) -> PasswordResetOTP | None:
    otp = (
        PasswordResetOTP.objects.filter(
            user=user,
            otp_code=otp_code,
            is_used=False,
        )
        .order_by("-created_at")
        .first()
    )

    if not otp:
        return None

    if otp.is_expired:
        return None

    return otp