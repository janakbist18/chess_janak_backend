from rest_framework.permissions import BasePermission


class IsRoomParticipant(BasePermission):
    message = "You are not a participant of this room."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        return obj.participants.filter(user=user).exists() or obj.host_id == user.id