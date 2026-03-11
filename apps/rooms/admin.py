from django.contrib import admin

from apps.rooms.models import GameRoom, RoomParticipant


class RoomParticipantInline(admin.TabularInline):
    model = RoomParticipant
    extra = 0
    autocomplete_fields = ("user",)
    readonly_fields = ("joined_at", "created_at", "updated_at")


@admin.register(GameRoom)
class GameRoomAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "room_code",
        "invite_code",
        "status",
        "host",
        "player_white",
        "player_black",
        "current_turn",
        "is_active",
        "created_at",
    )
    list_filter = ("status", "is_active", "room_type", "current_turn")
    search_fields = (
        "room_code",
        "invite_code",
        "host__email",
        "host__username",
        "player_white__email",
        "player_black__email",
    )
    autocomplete_fields = ("host", "player_white", "player_black", "winner")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [RoomParticipantInline]


@admin.register(RoomParticipant)
class RoomParticipantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "room",
        "user",
        "role",
        "side",
        "presence_status",
        "is_ready",
        "joined_at",
    )
    list_filter = ("role", "side", "presence_status", "is_ready")
    search_fields = (
        "room__room_code",
        "room__invite_code",
        "user__email",
        "user__username",
    )
    autocomplete_fields = ("room", "user")
    readonly_fields = ("joined_at", "created_at", "updated_at")