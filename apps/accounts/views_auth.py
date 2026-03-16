"""
Authentication API views (OTP login, registration, Gmail, Google Sign-in)
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate

from apps.accounts.models import User
from apps.accounts.services.otp_service import OTPService
from apps.accounts.services.jwt_service import JWTService
from apps.accounts.services.google_auth_service import handle_google_login
from apps.accounts.serializers import UserSerializer


class AuthViewSet(viewsets.ViewSet):
    """Authentication endpoints"""

    permission_classes = [AllowAny]

    @action(detail=False, methods=["post"])
    def send_otp(self, request):
        """Send OTP to email for login/registration"""
        email = request.data.get('email')
        purpose = request.data.get('purpose', 'login')  # login or registration

        if not email:
            return Response(
                {"error": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
            purpose = 'login' if purpose == 'login' else 'email_verify'
        except User.DoesNotExist:
            if purpose == 'registration':
                user = None
            else:
                return Response(
                    {"error": "Email not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

        success, message = OTPService.send_otp_email(email, purpose, user)

        if success:
            return Response(
                {
                    "message": message,
                    "email": email,
                    "purpose": purpose,
                },
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": message},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=["post"])
    def verify_otp(self, request):
        """Verify OTP and return access token"""
        email = request.data.get('email')
        otp_code = request.data.get('otp_code')
        username = request.data.get('username')  # For registration
        name = request.data.get('name')  # For registration
        purpose = request.data.get('purpose', 'login')

        if not email or not otp_code:
            return Response(
                {"error": "Email and OTP code are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        success, message, user = OTPService.verify_otp(email, otp_code, purpose)

        if not success:
            return Response(
                {"error": message},
                status=status.HTTP_400_BAD_REQUEST
            )

        # New user registration
        if user is None and purpose == 'registration':
            if not username or not name:
                return Response(
                    {"error": "Username and name required for registration"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                user = User.objects.create_user(
                    email=email,
                    username=username,
                    name=name,
                    is_verified=True,
                )
            except Exception as e:
                return Response(
                    {"error": f"Registration failed: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if not user:
            return Response(
                {"error": "Authentication failed"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Generate tokens
        tokens = JWTService.get_tokens_for_user(user)

        return Response(
            {
                "message": "Authentication successful",
                "user": UserSerializer(user).data,
                "tokens": tokens,
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["post"])
    def resend_otp(self, request):
        """Resend OTP to email"""
        email = request.data.get('email')
        purpose = request.data.get('purpose', 'login')

        if not email:
            return Response(
                {"error": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        success, message = OTPService.resend_otp(email, purpose)

        if success:
            return Response(
                {"message": message},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": message},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """Logout user (invalidate token)"""
        return Response(
            {"message": "Logged out successfully"},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["post"])
    def google_signin(self, request):
        """Google Sign-in endpoint

        Expects:
        {
            "id_token": "google_id_token_from_client"
        }

        Returns:
        {
            "message": "Authentication successful",
            "user": {...user_data...},
            "tokens": {
                "access": "...",
                "refresh": "..."
            }
        }
        """
        id_token = request.data.get('id_token')

        if not id_token:
            return Response(
                {"error": "Google ID token is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = handle_google_login(id_token)
            user = result['user']
            tokens = result['tokens']

            return Response(
                {
                    "message": "Google authentication successful",
                    "user": UserSerializer(user).data,
                    "tokens": tokens,
                },
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Google authentication failed: {str(e)}"},
                status=status.HTTP_401_UNAUTHORIZED
            )

    @action(detail=False, methods=["post"])
    def refresh_token(self, request):
        """Refresh access token using refresh token"""
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return Response(
                {"error": "Refresh token is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        success, access_token, error = JWTService.refresh_access_token(refresh_token)

        if success:
            return Response(
                {"access": access_token},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": error},
                status=status.HTTP_401_UNAUTHORIZED
            )


class UserPreferencesViewSet(viewsets.ViewSet):
    """User preferences endpoints"""

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get", "post"])
    def preferences(self, request):
        """Get or update user preferences"""
        user = request.user

        if request.method == "GET":
            try:
                prefs = user.preferences
                return Response({
                    "theme": prefs.theme,
                    "sound_enabled": prefs.sound_enabled,
                    "move_sound": prefs.move_sound,
                    "capture_sound": prefs.capture_sound,
                    "check_sound": prefs.check_sound,
                    "notifications_enabled": prefs.notifications_enabled,
                    "language": prefs.language,
                })
            except:
                return Response({"error": "Preferences not found"}, status=404)

        elif request.method == "POST":
            try:
                from apps.accounts.models_preferences import UserPreferences
                prefs, created = UserPreferences.objects.get_or_create(user=user)

                # Update fields
                if 'theme' in request.data:
                    prefs.theme = request.data['theme']
                if 'sound_enabled' in request.data:
                    prefs.sound_enabled = request.data['sound_enabled']
                if 'move_sound' in request.data:
                    prefs.move_sound = request.data['move_sound']
                if 'language' in request.data:
                    prefs.language = request.data['language']

                prefs.save()

                return Response({
                    "message": "Preferences updated",
                    "preferences": {
                        "theme": prefs.theme,
                        "sound_enabled": prefs.sound_enabled,
                        "language": prefs.language,
                    }
                })
            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
