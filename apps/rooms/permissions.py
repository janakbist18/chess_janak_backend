from rest_framework.permissions import BasePermission


class IsRoomParticipant(BasePermission):
    """
    Allow access only to room participants or room host.
    Works with device_id based authentication.
    """
    message = "You are not a participant of this room."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user:
            return False

        # Check if user is host or a participant
        return (obj.participants.filter(user=user).exists() or
                obj.host_id == user.id)