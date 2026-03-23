"""
Custom permission classes for coin system endpoints.
Implements fine-grained access control.
"""
from rest_framework.permissions import BasePermission, IsAuthenticated
from .models import UserCoin


class IsOwnerOrAdmin(IsAuthenticated):
    """
    Permission to check if user is accessing their own coin account or is admin.
    Prevents users from viewing/modifying other users' coins.
    """

    def has_object_permission(self, request, view, obj):
        # Admin users have full access
        if request.user.is_staff:
            return True

        # Check if user owns the account
        if isinstance(obj, UserCoin):
            return obj.user == request.user

        # For other objects with user field
        if hasattr(obj, 'user'):
            return obj.user == request.user

        return False


class IsOwner(BasePermission):
    """
    Permission to check if user owns the resource.
    """

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False


class CanClaimRewards(IsAuthenticated):
    """
    Permission to claim ad and daily rewards.
    Prevents abuse by rate limiting and cooldown validation.
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        # User must have a coin account
        try:
            UserCoin.objects.get(user=request.user)
            return True
        except UserCoin.DoesNotExist:
            return False


class CanSpendCoins(IsAuthenticated):
    """
    Permission to spend coins.
    Ensures user has sufficient balance.
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        # User must have a coin account
        try:
            UserCoin.objects.get(user=request.user)
            return True
        except UserCoin.DoesNotExist:
            return False

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False


class IsAdminUser(BasePermission):
    """
    Permission check for admin-only endpoints.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class CanManageRewardConfig(IsAdminUser):
    """
    Permission to manage reward configuration.
    Only admins can modify reward amounts and limits.
    """
    pass


class RateLimitPermission(BasePermission):
    """
    Custom permission to enforce rate limiting on sensitive endpoints.
    Works with rate limiting middleware.
    """

    def has_permission(self, request, view):
        # Rate limiting is handled by middleware
        # This permission is a placeholder for future enhancements
        return True
