"""
Simplified authentication endpoints for device_id based anonymous access.
"""
import uuid
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model

User = get_user_model()


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        """Health check endpoint"""
        return Response(
            {
                "message": "Chess Janak API is running",
                "status": "ok",
                "auth_type": "device_id",
                "version": "2.0",
            },
            status=status.HTTP_200_OK
        )


class GetDeviceIDView(APIView):
    """
    Generate a new device_id for anonymous users.
    Can be called before making requests to get a consistent device identifier.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        POST /api/auth/device-id/
        Generate a new device_id for the client
        Returns device_id that should be sent in X-Device-ID header
        """
        device_id = str(uuid.uuid4())

        try:
            # Create anonymous user for this device
            user = User.objects.create_anonymous_user(device_id=device_id)

            return Response(
                {
                    "success": True,
                    "device_id": device_id,
                    "message": "Device ID generated. Include this in X-Device-ID header for all requests.",
                    "user_id": user.id,
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": str(e),
                    "device_id": device_id,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CurrentUserView(APIView):
    """Get current user information based on device_id"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        GET /api/auth/me/
        Returns current user information
        """
        user = request.user

        if not user or not user.id:
            return Response(
                {
                    "success": False,
                    "error": "User not found",
                    "message": "No valid device_id provided. Include X-Device-ID header.",
                },
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                "success": True,
                "user_id": user.id,
                "device_id": user.device_id,
                "is_anonymous": user.is_anonymous,
                "username": user.username,
                "name": user.name,
                "profile_image": user.profile_image.url if user.profile_image else None,
                "is_verified": user.is_verified,
                "date_joined": user.date_joined,
            },
            status=status.HTTP_200_OK
        )


class AuthStatusView(APIView):
    """Get authentication status"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        GET /api/auth/status/
        Returns current authentication status
        """
        user = request.user
        device_id = getattr(request, 'device_id', None)

        return Response(
            {
                "authenticated": bool(user and user.id),
                "auth_type": "device_id",
                "device_id": device_id,
                "user_id": user.id if user and user.id else None,
                "is_anonymous": user.is_anonymous if user and user.id else True,
            },
            status=status.HTTP_200_OK
        )
