from django.contrib import admin

from apps.chessplay.models import ChessMatch, ChessMove


class ChessMoveInline(admin.TabularInline):
    model = ChessMove
    extra = 0
    readonly_fields = (
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
        "is_checkmate",
        "created_at",
    )


@admin.register(ChessMatch)
class ChessMatchAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "room",
        "white_player",
        "black_player",
        "status",
        "result",
        "result_type",
        "winner",
        "is_check",
        "is_checkmate",
        "is_stalemate",
        "started_at",
        "ended_at",
    )
    list_filter = (
        "status",
        "result",
        "result_type",
        "is_check",
        "is_checkmate",
        "is_stalemate",
    )
    search_fields = (
        "room__room_code",
        "room__invite_code",
        "white_player__username",
        "black_player__username",
        "white_player__email",
        "black_player__email",
    )
    autocomplete_fields = (
        "room",
        "white_player",
        "black_player",
        "winner",
        "draw_offered_by",
    )
    readonly_fields = ("created_at", "updated_at")
    inlines = [ChessMoveInline]


@admin.register(ChessMove)
class ChessMoveAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "match",
        "move_number",
        "player",
        "side",
        "from_square",
        "to_square",
        "uci",
        "san",
        "is_capture",
        "is_check",
        "is_checkmate",
        "created_at",
    )
    list_filter = ("side", "is_capture", "is_check", "is_checkmate")
    search_fields = (
        "match__room__room_code",
        "player__username",
        "player__email",
        "uci",
        "san",
    )
    autocomplete_fields = ("match", "player")
    readonly_fields = ("created_at", "updated_at")