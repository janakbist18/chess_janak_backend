from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.chessplay.models import ChessMatch, ChessMove


class ChessMoveSerializer(serializers.ModelSerializer):
    player = UserSerializer(read_only=True)

    class Meta:
        model = ChessMove
        fields = (
            "id",
            "match",
            "move_number",
            "player",
            "side",
            "from_square",
            "to_square",
            "uci",
            "san",
            "promotion_piece",
            "fen_after",
            "is_capture",
            "is_check",
            "created_at",
        )
        read_only_fields = (
            "id",
            "match",
            "fen_after",
            "created_at",
        )


class ChessMatchSerializer(serializers.ModelSerializer):
    white_player = UserSerializer(read_only=True)
    black_player = UserSerializer(read_only=True)
    winner = UserSerializer(read_only=True)
    draw_offered_by = UserSerializer(read_only=True)
    moves = ChessMoveSerializer(many=True, read_only=True)
    room_id = serializers.CharField(source="room.id", read_only=True)

    class Meta:
        model = ChessMatch
        fields = (
            "id",
            "room_id",
            "white_player",
            "black_player",
            "winner",
            "draw_offered_by",
            "status",
            "result",
            "result_type",
            "initial_fen",
            "current_fen",
            "pgn",
            "halfmove_clock",
            "fullmove_number",
            "is_check",
            "is_checkmate",
            "is_stalemate",
            "started_at",
            "ended_at",
            "moves",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "room_id",
            "winner",
            "draw_offered_by",
            "current_fen",
            "pgn",
            "halfmove_clock",
            "fullmove_number",
            "is_check",
            "is_checkmate",
            "is_stalemate",
            "ended_at",
            "created_at",
            "updated_at",
        )
