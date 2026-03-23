"""
Fast and non-blocking email service
"""
import threading
from django.core.mail import send_mail as django_send_mail
from django.conf import settings


def send_email_async(subject: str, message: str, recipient_list: list) -> None:
    """Send email in background thread to avoid blocking response"""
    def _send():
        try:
            django_send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                fail_silently=True,
            )
        except Exception as e:
            print(f"Email sending failed: {e}")

    # Send in background thread
    thread = threading.Thread(target=_send, daemon=True)
    thread.start()


def send_otp_email(email: str, otp_code: str, name: str = "User") -> None:
    """Send OTP to email asynchronously"""
    subject = "Chess Janak - Verify Your Email"
    message = (
        f"Hello {name},\n\n"
        f"Your verification OTP is: {otp_code}\n"
        f"This OTP will expire in 10 minutes.\n\n"
        f"If you didn't request this, please ignore this email.\n\n"
        f"Thanks,\nChess Janak Team"
    )
    send_email_async(subject, message, [email])


def send_password_reset_email(email: str, otp_code: str, name: str = "User") -> None:
    """Send password reset OTP to email asynchronously"""
    subject = "Chess Janak - Password Reset"
    message = (
        f"Hello {name},\n\n"
        f"Your password reset OTP is: {otp_code}\n"
        f"This OTP will expire in 10 minutes.\n\n"
        f"If you didn't request this, please ignore this email.\n\n"
        f"Thanks,\nChess Janak Team"
    )
    send_email_async(subject, message, [email])
