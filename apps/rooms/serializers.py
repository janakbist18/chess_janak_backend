from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.rooms.models import GameRoom, RoomParticipant
from apps.rooms.utils import build_room_invite_link


class RoomParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = RoomParticipant
        fields = (
            "id",
            "user",
            "role",
            "side",
            "presence_status",
            "is_ready",
            "joined_at",
            "left_at",
            "last_ping_at",
        )


class GameRoomSerializer(serializers.ModelSerializer):
    host = UserSerializer(read_only=True)
    player_white = UserSerializer(read_only=True)
    player_black = UserSerializer(read_only=True)
    winner = UserSerializer(read_only=True)
    participants = RoomParticipantSerializer(many=True, read_only=True)
    invite_link = serializers.SerializerMethodField()
    player_count = serializers.IntegerField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)

    class Meta:
        model = GameRoom
        fields = (
            "id",
            "room_code",
            "invite_code",
            "invite_link",
            "room_type",
            "status",
            "host",
            "player_white",
            "player_black",
            "winner",
            "current_turn",
            "fen",
            "pgn",
            "is_active",
            "is_full",
            "player_count",
            "participants",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        )

    def get_invite_link(self, obj):
        return build_room_invite_link(obj.invite_code)


class CreateRoomSerializer(serializers.Serializer):
    def create(self, validated_data):
        return validated_data


class JoinRoomSerializer(serializers.Serializer):
    invite_code = serializers.CharField(required=False, allow_blank=False)
    room_id = serializers.UUIDField(required=False)

    def validate(self, attrs):
        invite_code = attrs.get("invite_code")
        room_id = attrs.get("room_id")

        if not invite_code and not room_id:
            raise serializers.ValidationError(
                "Either invite_code or room_id is required."
            )

        return attrs