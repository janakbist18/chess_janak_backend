from rest_framework.permissions import BasePermission

from apps.rooms.models import GameRoom


class IsRoomChessPlayer(BasePermission):
    message = "You are not a chess player in this room."

    def has_permission(self, request, view):
        room_id = view.kwargs.get("room_id")
        if not room_id or not request.user or not request.user.is_authenticated:
            return False

        room = GameRoom.objects.filter(id=room_id).first()
        if not room:
            return False

        return request.user.id in [room.player_white_id, room.player_black_id]