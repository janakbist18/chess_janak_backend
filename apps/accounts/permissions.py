from rest_framework.permissions import BasePermission


class IsVerifiedUser(BasePermission):
    message = "Your account is not verified yet."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_verified)