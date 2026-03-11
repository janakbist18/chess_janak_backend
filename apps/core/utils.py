import random
import string


def generate_numeric_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def generate_short_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choices(alphabet, k=length))