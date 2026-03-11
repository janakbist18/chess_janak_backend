from django.db.models import Q

from apps.rooms.models import GameRoom


def get_user_rooms(user):
    return (
        GameRoom.objects.filter(
            Q(host=user) | Q(player_white=user) | Q(player_black=user)
        )
        .select_related("host", "player_white", "player_black", "winner")
        .prefetch_related("participants", "participants__user")
        .distinct()
        .order_by("-created_at")
    )


def get_room_for_user(room_id, user):
    return (
        GameRoom.objects.filter(id=room_id)
        .filter(Q(host=user) | Q(player_white=user) | Q(player_black=user))
        .select_related("host", "player_white", "player_black", "winner")
        .prefetch_related("participants", "participants__user")
        .first()
    )


def get_room_by_invite_code(invite_code):
    return (
        GameRoom.objects.filter(invite_code__iexact=invite_code, is_active=True)
        .select_related("host", "player_white", "player_black", "winner")
        .prefetch_related("participants", "participants__user")
        .first()
    )