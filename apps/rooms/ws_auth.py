import uuid
from urllib.parse import parse_qs

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@sync_to_async
def get_user_from_device_id(device_id: str):
    """
    Get or create user from device_id.
    Used for WebSocket connections with device-based authentication.
    """
    if not device_id:
        # Generate new device_id if not provided
        device_id = str(uuid.uuid4())

    try:
        # Try to get existing user
        user = User.objects.get(device_id=device_id)
        return user
    except User.DoesNotExist:
        # Create new anonymous user
        try:
            user = User.objects.create_anonymous_user(device_id=device_id)
            logger.info(f"Created new WebSocket user with device_id: {device_id[:8]}")
            return user
        except Exception as e:
            logger.error(f"Error creating anonymous user for WebSocket: {str(e)}")
            return AnonymousUser()


class QueryStringDeviceIDAuthMiddleware:
    """
    WebSocket middleware for device_id based authentication.
    Replaces JWT token authentication with device_id from query parameters.

    Usage: ws://localhost/ws/room/123/?device_id=xxx
    """
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)

        # Get device_id from query parameters
        device_id = query_params.get("device_id", [None])[0]

        # Get or create user
        scope["user"] = await get_user_from_device_id(device_id)
        scope["device_id"] = device_id

        return await self.inner(scope, receive, send)


def QueryStringDeviceIDAuthMiddlewareStack(inner):
    """Wrapper for WebSocket middleware stack"""
    return QueryStringDeviceIDAuthMiddleware(inner)


# Backward compatibility: Keep JWT middleware as fallback
@sync_to_async
def get_user_from_token(token: str):
    """Legacy JWT token authentication (fallback)"""
    if not token:
        return AnonymousUser()

    try:
        from rest_framework_simplejwt.authentication import JWTAuthentication
        jwt_auth = JWTAuthentication()
        validated_token = jwt_auth.get_validated_token(token)
        user = jwt_auth.get_user(validated_token)
        return user
    except Exception:
        return AnonymousUser()


class QueryStringJWTAuthMiddleware:
    """Legacy JWT authentication middleware (kept for backward compatibility)"""
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)

        token = query_params.get("token", [None])[0]
        scope["user"] = await get_user_from_token(token)

        return await self.inner(scope, receive, send)


def QueryStringJWTAuthMiddlewareStack(inner):
    """Legacy wrapper for backward compatibility"""
    return QueryStringJWTAuthMiddleware(inner)