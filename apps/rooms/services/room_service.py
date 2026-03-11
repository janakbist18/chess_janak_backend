from django.db import transaction

from apps.rooms.models import GameRoom, RoomParticipant
from apps.rooms.services.invite_service import (
    generate_unique_invite_code,
    generate_unique_room_code,
)


@transaction.atomic
def create_room_for_user(user) -> GameRoom:
    room = GameRoom.objects.create(
        room_code=generate_unique_room_code(),
        invite_code=generate_unique_invite_code(),
        host=user,
        player_white=user,
        player_black=None,
        status=GameRoom.STATUS_WAITING,
        current_turn=GameRoom.SIDE_WHITE,
    )

    RoomParticipant.objects.create(
        room=room,
        user=user,
        role=RoomParticipant.ROLE_HOST,
        side=RoomParticipant.SIDE_WHITE,
        presence_status=RoomParticipant.PRESENCE_JOINED,
        is_ready=True,
    )

    return room


@transaction.atomic
def join_room_for_user(room: GameRoom, user):
    if room.player_white_id == user.id or room.player_black_id == user.id:
        participant = room.participants.filter(user=user).first()
        return room, participant, False

    if room.status in [GameRoom.STATUS_FINISHED, GameRoom.STATUS_CANCELLED]:
        raise ValueError("This room is no longer available.")

    if room.player_white and room.player_black:
        raise ValueError("This room is already full.")

    assigned_side = None

    if room.player_white is None:
        room.player_white = user
        assigned_side = RoomParticipant.SIDE_WHITE
    elif room.player_black is None:
        room.player_black = user
        assigned_side = RoomParticipant.SIDE_BLACK

    if room.player_white and room.player_black:
        room.status = GameRoom.STATUS_READY
    else:
        room.status = GameRoom.STATUS_WAITING

    room.save()

    participant = RoomParticipant.objects.create(
        room=room,
        user=user,
        role=RoomParticipant.ROLE_PLAYER,
        side=assigned_side or RoomParticipant.SIDE_SPECTATOR,
        presence_status=RoomParticipant.PRESENCE_JOINED,
        is_ready=True,
    )

    return room, participant, True


def can_user_start_room(room: GameRoom) -> bool:
    return bool(room.player_white and room.player_black and room.status == GameRoom.STATUS_READY)