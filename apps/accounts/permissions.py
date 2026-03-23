from rest_framework.permissions import BasePermission


class IsVerifiedUser(BasePermission):
    """
    Allow access to verified users.
    For anonymous users, this is always True since they're auto-verified.
    For authenticated users, check is_verified flag.
    """
    message = "Your account is not verified yet."

    def has_permission(self, request, view):
        user = request.user
        # All authenticated users (including anonymous) are allowed
        # Anonymous users are automatically verified
        # For authenticated users, check is_verified flag
        if not user:
            return False
        if user.is_anonymous:
            return True
        return bool(user.is_verified)