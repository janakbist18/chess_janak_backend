from apps.accounts.serializers import UserSerializer
from apps.rooms.models import GameRoom


def serialize_user(user, request=None):
    if not user:
        return None
    return UserSerializer(user, context={"request": request}).data


def serialize_room_state(room: GameRoom, request=None) -> dict:
    participants = []
    for participant in room.participants.select_related("user").all().order_by("joined_at"):
        participants.append(
            {
                "id": participant.id,
                "role": participant.role,
                "side": participant.side,
                "presence_status": participant.presence_status,
                "is_ready": participant.is_ready,
                "joined_at": participant.joined_at.isoformat() if participant.joined_at else None,
                "left_at": participant.left_at.isoformat() if participant.left_at else None,
                "user": serialize_user(participant.user, request=request),
            }
        )

    return {
        "id": str(room.id),
        "room_code": room.room_code,
        "invite_code": room.invite_code,
        "status": room.status,
        "current_turn": room.current_turn,
        "fen": room.fen,
        "pgn": room.pgn,
        "is_active": room.is_active,
        "player_count": room.player_count,
        "is_full": room.is_full,
        "host": serialize_user(room.host, request=request),
        "player_white": serialize_user(room.player_white, request=request),
        "player_black": serialize_user(room.player_black, request=request),
        "winner": serialize_user(room.winner, request=request),
        "participants": participants,
        "started_at": room.started_at.isoformat() if room.started_at else None,
        "finished_at": room.finished_at.isoformat() if room.finished_at else None,
        "created_at": room.created_at.isoformat() if room.created_at else None,
        "updated_at": room.updated_at.isoformat() if room.updated_at else None,
    }