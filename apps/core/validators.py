import re

from django.core.exceptions import ValidationError


def validate_username_format(value: str) -> str:
    pattern = r"^[a-zA-Z0-9_.]+$"
    if not re.match(pattern, value):
        raise ValidationError(
            "Username may contain only letters, numbers, underscore, and dot."
        )
    return value