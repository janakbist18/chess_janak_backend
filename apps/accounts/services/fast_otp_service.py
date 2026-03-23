"""
Fast OTP service with optimized queries
"""
import random
from datetime import timedelta

from django.utils import timezone
from django.conf import settings

from apps.accounts.models import EmailOTP, User
from apps.accounts.services.fast_email_service import send_otp_email, send_password_reset_email


def generate_otp() -> str:
    """Generate 6-digit OTP"""
    return "".join([str(random.randint(0, 9)) for _ in range(6)])


def create_and_send_otp(user: User, purpose: str = "registration") -> None:
    """Create OTP and send email asynchronously"""
    # Invalidate old OTPs
    EmailOTP.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)

    # Create new OTP
    otp_code = generate_otp()
    expires_at = timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

    EmailOTP.objects.create(
        user=user,
        email=user.email,
        otp_code=otp_code,
        purpose=purpose,
        expires_at=expires_at,
    )

    # Send email asynchronously (non-blocking)
    send_otp_email(user.email, otp_code, user.name)


def verify_otp(email: str, otp_code: str, purpose: str = "registration") -> tuple:
    """Verify OTP - Returns (success: bool, user: User or None)"""
    try:
        # Get user with single query
        user = User.objects.filter(email__iexact=email).select_related("profile").first()
        if not user:
            return False, None

        # Get latest OTP
        otp = EmailOTP.objects.filter(
            user=user,
            otp_code=otp_code,
            purpose=purpose,
            is_used=False
        ).latest("created_at")

        # Check expiry
        if otp.is_expired:
            return False, None

        # Mark as used
        otp.mark_used()

        return True, user

    except EmailOTP.DoesNotExist:
        return False, None
    except Exception as e:
        print(f"OTP verification error: {e}")
        return False, None


def resend_otp(email: str, purpose: str = "registration") -> bool:
    """Resend OTP to email"""
    user = User.objects.filter(email__iexact=email).first()
    if user:
        create_and_send_otp(user, purpose)
        return True
    return False
