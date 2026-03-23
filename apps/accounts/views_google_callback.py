"""
Google OAuth callback view for authorization code flow
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.http import JsonResponse

from apps.accounts.services.google_auth_service import handle_google_login


class GoogleCallbackView(APIView):
    """
    Google OAuth callback endpoint
    Handles both:
    1. ID token from mobile/web (token-based)
    2. Authorization code from web OAuth flow
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        GET /api/auth/google/callback/?code=AUTHORIZATION_CODE&state=STATE
        Handles authorization code flow callback
        """
        code = request.query_params.get("code")
        error = request.query_params.get("error")

        if error:
            return JsonResponse(
                {
                    "error": error,
                    "error_description": request.query_params.get("error_description", ""),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not code:
            return JsonResponse(
                {"error": "Authorization code not provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Note: In a full OAuth 2.0 flow, you would exchange the code for tokens
        # This is a simplified version. For production, implement proper token exchange.
        return JsonResponse(
            {
                "message": "Authorization code received. Implement token exchange.",
                "code": code,
            }
        )

    def post(self, request):
        """
        POST /api/auth/google/callback/
        {
            "id_token": "GOOGLE_ID_TOKEN"
        }
        Token-based authentication (recommended for Flutter web)
        """
        id_token = request.data.get("id_token")

        if not id_token:
            return Response(
                {"error": "ID token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = handle_google_login(id_token)
            user = result["user"]
            tokens = result["tokens"]

            return Response(
                {
                    "message": "Google sign-in successful.",
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "username": user.username,
                        "name": user.name,
                        "is_verified": user.is_verified,
                    },
                    "tokens": tokens,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
