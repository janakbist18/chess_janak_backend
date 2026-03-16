from django.contrib import admin

from apps.chessplay.models import ChessMatch, ChessMove
from apps.chessplay.models_ads import RewardAd, UserAdReward, AdViewerSession


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


@admin.register(RewardAd)
class RewardAdAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "ad_type",
        "status",
        "reward_coins",
        "reward_points",
        "duration_seconds",
        "total_impressions",
        "total_completions",
        "is_available",
        "created_at",
    )
    list_filter = ("ad_type", "status", "created_at")
    search_fields = ("title", "description")
    readonly_fields = (
        "total_impressions",
        "total_completions",
        "total_clicks",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        ("Basic Info", {
            "fields": ("title", "description", "ad_type", "status")
        }),
        ("Rewards", {
            "fields": ("reward_coins", "reward_points")
        }),
        ("Ad Settings", {
            "fields": ("duration_seconds", "impressions_limit", "daily_limit_per_user")
        }),
        ("URLs", {
            "fields": ("ad_url", "thumbnail_url")
        }),
        ("Scheduling", {
            "fields": ("starts_at", "ends_at")
        }),
        ("Tracking", {
            "fields": ("total_impressions", "total_completions", "total_clicks")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )


@admin.register(UserAdReward)
class UserAdRewardAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "ad",
        "viewed_at",
        "completed",
        "coins_earned",
        "points_earned",
        "clicked",
    )
    list_filter = ("completed", "clicked", "viewed_at")
    search_fields = (
        "user__email",
        "user__username",
        "ad__title",
    )
    readonly_fields = (
        "viewed_at",
        "completed_at",
        "coins_earned",
        "points_earned",
        "clicked_at",
    )
    autocomplete_fields = ("user", "ad")


@admin.register(AdViewerSession)
class AdViewerSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "ad",
        "started_at",
        "ended_at",
        "watch_duration_seconds",
        "skipped",
    )
    list_filter = ("skipped", "started_at")
    search_fields = (
        "user__email",
        "user__username",
        "ad__title",
    )
    readonly_fields = ("started_at", "ended_at", "skipped_at")
    autocomplete_fields = ("user", "ad")