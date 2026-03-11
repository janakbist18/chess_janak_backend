from django.core.exceptions import ValidationError


def validate_password_confirmation(password: str, confirm_password: str) -> None:
    if password != confirm_password:
        raise ValidationError("Password and confirm password do not match.")


def validate_new_passwords(password: str, confirm_password: str) -> None:
    if password != confirm_password:
        raise ValidationError("New password and confirm password do not match.")