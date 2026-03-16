"""
Email OTP service for authentication
"""
import random
import string
from datetime import timedelta
from typing import Tuple, Optional
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

from apps.accounts.models import EmailOTP, User


class OTPService:
    """Service for managing OTP (One-Time Password) authentication"""

    OTP_LENGTH = 6
    OTP_VALIDITY_MINUTES = 10

    @staticmethod
    def generate_otp() -> str:
        """Generate random 6-digit OTP"""
        return ''.join(random.choices(string.digits, k=OTPService.OTP_LENGTH))

    @classmethod
    def send_otp_email(
        cls,
        email: str,
        purpose: str = EmailOTP.PURPOSE_LOGIN,
        user: Optional[User] = None
    ) -> Tuple[bool, str]:
        """
        Send OTP to email address
        Returns: (success, message)
        """
        try:
            # Generate OTP code
            otp_code = cls.generate_otp()

            # Determine user for the OTP record
            if not user:
                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    # For registration, we need to create a temporary user or handle differently
                    # For now, we'll use a temp approach with email
                    pass

            # Create or update OTP record
            expires_at = timezone.now() + timedelta(minutes=cls.OTP_VALIDITY_MINUTES)

            if user:
                otp_obj = EmailOTP.objects.create(
                    user=user,
                    email=email,
                    otp_code=otp_code,
                    purpose=purpose,
                    expires_at=expires_at,
                )
            else:
                # For registration flow
                from django.contrib.auth.models import AnonymousUser
                # Store OTP temporarily (you might want to use cache instead)
                otp_obj = type('TempOTP', (), {
                    'otp_code': otp_code,
                    'email': email,
                    'purpose': purpose,
                })()

            # Prepare email content
            subject = cls._get_email_subject(purpose)
            context = {
                'otp_code': otp_code,
                'otp_validity_minutes': cls.OTP_VALIDITY_MINUTES,
                'purpose': purpose,
            }

            html_message = render_to_string('emails/otp_email.html', context)
            plain_message = render_to_string('emails/otp_email.txt', context)

            # Send email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False,
            )

            return True, f"OTP sent to {email}"

        except Exception as e:
            print(f"Error sending OTP: {str(e)}")
            return False, f"Error sending OTP: {str(e)}"

    @staticmethod
    def _get_email_subject(purpose: str) -> str:
        """Get email subject based on purpose"""
        subjects = {
            EmailOTP.PURPOSE_LOGIN: "Your Login OTP Code",
            EmailOTP.PURPOSE_REGISTRATION: "Verify Your Registration - OTP Code",
            EmailOTP.PURPOSE_EMAIL_VERIFY: "Verify Your Email Address - OTP Code",
        }
        return subjects.get(purpose, "Your OTP Code")

    @staticmethod
    def verify_otp(
        email: str,
        otp_code: str,
        purpose: str = EmailOTP.PURPOSE_LOGIN
    ) -> Tuple[bool, str, Optional[User]]:
        """
        Verify OTP code
        Returns: (success, message, user)
        """
        try:
            # Find OTP record
            otp = EmailOTP.objects.filter(
                email=email,
                otp_code=otp_code,
                purpose=purpose,
                is_used=False
            ).latest('created_at')

            # Check if OTP is expired
            if otp.is_expired:
                return False, "OTP has expired", None

            # Mark OTP as used
            otp.mark_used()

            # Get user
            user = otp.user

            return True, "OTP verified successfully", user

        except EmailOTP.DoesNotExist:
            return False, "Invalid OTP code", None
        except Exception as e:
            return False, f"Error verifying OTP: {str(e)}", None

    @staticmethod
    def resend_otp(email: str, purpose: str = EmailOTP.PURPOSE_LOGIN) -> Tuple[bool, str]:
        """
        Resend OTP to email
        """
        try:
            user = User.objects.get(email=email)
            return OTPService.send_otp_email(email, purpose, user)
        except User.DoesNotExist:
            return False, "User not found"
        except Exception as e:
            return False, f"Error: {str(e)}"

    @staticmethod
    def cleanup_expired_otps():
        """Delete expired OTP records"""
        expired_count = EmailOTP.objects.filter(
            expires_at__lte=timezone.now()
        ).delete()[0]
        return expired_count


# Wrapper functions for backward compatibility
def create_email_verification_otp(email: str, user: Optional[User] = None) -> Tuple[bool, str]:
    """Create and send email verification OTP"""
    return OTPService.send_otp_email(email, EmailOTP.PURPOSE_EMAIL_VERIFY, user)


def create_password_reset_otp(email: str, user: Optional[User] = None) -> Tuple[bool, str]:
    """Create and send password reset OTP"""
    return OTPService.send_otp_email(email, EmailOTP.PURPOSE_REGISTRATION, user)


def get_valid_email_otp(email: str, otp_code: str) -> Tuple[bool, str, Optional[User]]:
    """Verify email OTP"""
    return OTPService.verify_otp(email, otp_code, EmailOTP.PURPOSE_EMAIL_VERIFY)


def get_valid_password_reset_otp(email: str, otp_code: str) -> Tuple[bool, str, Optional[User]]:
    """Verify password reset OTP"""
    return OTPService.verify_otp(email, otp_code, EmailOTP.PURPOSE_REGISTRATION)
