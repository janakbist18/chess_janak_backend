from django.conf import settings
from django.core.mail import send_mail


def send_plain_email(subject: str, message: str, recipient_list: list[str]) -> int:
    return send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        fail_silently=False,
    )


def send_registration_otp_email(name: str, email: str, otp_code: str) -> int:
    subject = "Chess Janak - Verify Your Email"
    message = (
        f"Hello {name},\n\n"
        f"Welcome to Chess Janak.\n"
        f"Your verification OTP is: {otp_code}\n"
        f"This OTP will expire soon.\n\n"
        f"If you did not request this, please ignore this email.\n\n"
        f"Thanks,\n"
        f"Chess Janak Team"
    )
    return send_plain_email(subject, message, [email])


def send_password_reset_otp_email(name: str, email: str, otp_code: str) -> int:
    subject = "Chess Janak - Password Reset OTP"
    message = (
        f"Hello {name},\n\n"
        f"Your password reset OTP is: {otp_code}\n"
        f"This OTP will expire soon.\n\n"
        f"If you did not request this, please ignore this email.\n\n"
        f"Thanks,\n"
        f"Chess Janak Team"
    )
    return send_plain_email(subject, message, [email])