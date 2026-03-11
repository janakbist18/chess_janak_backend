from apps.core.utils import generate_short_code
from apps.rooms.models import GameRoom


def generate_unique_room_code(length: int = 8) -> str:
    while True:
        code = generate_short_code(length)
        if not GameRoom.objects.filter(room_code=code).exists():
            return code


def generate_unique_invite_code(length: int = 8) -> str:
    while True:
        code = generate_short_code(length)
        if not GameRoom.objects.filter(invite_code=code).exists():
            return code