"""
Middleware for handling device_id-based anonymous user authentication.
Replaces JWT authentication with device_id header-based identification.
"""
import uuid
from django.contrib.auth import get_user_model
from django.utils.decorators import sync_and_async_middleware
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@sync_and_async_middleware
class DeviceIDMiddleware:
    """
    Middleware to handle device_id based anonymous user identification.

    Expected header: X-Device-ID (UUID string)
    If device_id is provided:
        - Retrieves existing user or creates new anonymous user
        - Attaches user to request
    If no device_id:
        - Generates new device_id
        - Creates new anonymous user
        - Attaches user to request
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._process_request(request)
        response = self.get_response(request)
        return response

    def _process_request(self, request):
        """Process incoming request and attach user based on device_id"""
        # Get device_id from header
        device_id = request.META.get('HTTP_X_DEVICE_ID', '').strip()

        # If no device_id provided, generate one
        if not device_id:
            device_id = str(uuid.uuid4())

        try:
            # Try to get existing user with this device_id
            user = User.objects.get(device_id=device_id)
            request.user = user
            request.device_id = device_id
        except User.DoesNotExist:
            # Create new anonymous user
            try:
                user = User.objects.create_anonymous_user(device_id=device_id)
                request.user = user
                request.device_id = device_id
                logger.info(f"Created new anonymous user with device_id: {device_id[:8]}")
            except Exception as e:
                logger.error(f"Error creating anonymous user: {str(e)}")
                # Fallback: create with auto-generated device_id
                user = User.objects.create_anonymous_user()
                request.user = user
                request.device_id = user.device_id


class DeviceIDWebSocketMiddleware:
    """
    WebSocket middleware for handling device_id in query parameters.
    Extracts device_id from query string and identifies user.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        """Handle WebSocket connection with device_id from URL parameters"""
        # This will be used with ASGI channels
        # The device_id should be passed in query parameters: ?device_id=xxx
        from urllib.parse import parse_qs

        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)

        device_id = query_params.get("device_id", [None])[0]

        if not device_id:
            device_id = str(uuid.uuid4())

        try:
            user = await self._get_or_create_user(device_id)
            scope["user"] = user
            scope["device_id"] = device_id
        except Exception as e:
            logger.error(f"Error getting WebSocket user: {str(e)}")
            scope["user"] = None
            scope["device_id"] = device_id

        return await self.inner(scope, receive, send)

    @staticmethod
    async def _get_or_create_user(device_id):
        """Get or create user from device_id (async version)"""
        from django.db import sync_to_async

        @sync_to_async
        def _get_or_create():
            try:
                return User.objects.get(device_id=device_id)
            except User.DoesNotExist:
                return User.objects.create_anonymous_user(device_id=device_id)

        return await _get_or_create()


def DeviceIDWebSocketMiddlewareStack(inner):
    """Wrapper for WebSocket middleware stack"""
    return DeviceIDWebSocketMiddleware(inner)
