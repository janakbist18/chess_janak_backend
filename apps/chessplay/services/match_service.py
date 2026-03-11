from django.db import transaction
from django.utils import timezone

from apps.chessplay.models import ChessMatch
from apps.rooms.models import GameRoom


@transaction.atomic
def get_or_create_match_for_room(room: GameRoom) -> ChessMatch:
    match, created = ChessMatch.objects.get_or_create(
        room=room,
        defaults={
            "white_player": room.player_white,
            "black_player": room.player_black,
            "status": ChessMatch.STATUS_WAITING,
            "initial_fen": room.fen,
            "current_fen": room.fen,
            "pgn": room.pgn,
        },
    )

    changed = False

    if room.player_white and match.white_player_id != room.player_white_id:
        match.white_player = room.player_white
        changed = True

    if room.player_black and match.black_player_id != room.player_black_id:
        match.black_player = room.player_black
        changed = True

    if room.player_white and room.player_black and match.status == ChessMatch.STATUS_WAITING:
        match.status = ChessMatch.STATUS_IN_PROGRESS
        if not match.started_at:
            match.started_at = timezone.now()
        changed = True

        if room.status != GameRoom.STATUS_IN_PROGRESS:
            room.status = GameRoom.STATUS_IN_PROGRESS
            if not room.started_at:
                room.started_at = timezone.now()
            room.save(update_fields=["status", "started_at", "updated_at"])

    if changed:
        match.save()

    return match