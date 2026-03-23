from rest_framework.permissions import BasePermission


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return bool(request.user and request.user.is_staff)


class IsOwnerOrReadOnly(BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    Allows read access to any request.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        # Write permissions are only allowed to the owner of the object
        # Check for various owner field names
        owner_field = getattr(obj, "owner", None) or getattr(obj, "user", None) or getattr(obj, "created_by", None)
        return owner_field == request.user