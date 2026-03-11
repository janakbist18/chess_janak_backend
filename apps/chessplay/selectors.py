from apps.chessplay.models import ChessMatch


def get_match_by_room_id(room_id):
    return (
        ChessMatch.objects.select_related(
            "room",
            "white_player",
            "black_player",
            "winner",
            "draw_offered_by",
        )
        .prefetch_related("moves", "moves__player")
        .filter(room_id=room_id)
        .first()
    )