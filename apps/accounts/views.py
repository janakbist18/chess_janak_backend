from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
import logging

from apps.accounts.models import ThemePreference
from apps.accounts.serializers import (
    ForgotPasswordSerializer,
    GoogleSignInSerializer,
    LoginSerializer,
    RegisterSerializer,
    ResendRegistrationOTPSerializer,
    ResetPasswordSerializer,
    ThemePreferenceSerializer,
    UserSerializer,
    VerifyRegistrationOTPSerializer,
)
from apps.accounts.services.auth_service import generate_tokens_for_user

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(
            {
                "message": "Accounts API is ready.",
                "phase": 2,
            }
        )


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                "message": "Registration successful. OTP sent to email.",
                "user": UserSerializer(user, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyRegistrationOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyRegistrationOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        user = result["user"]
        tokens = result["tokens"]

        return Response(
            {
                "message": "OTP verified successfully.",
                "user": UserSerializer(user, context={"request": request}).data,
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )


class ResendRegistrationOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResendRegistrationOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "A new OTP has been sent to your email."},
            status=status.HTTP_200_OK,
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        user.last_seen = timezone.now()
        user.save(update_fields=["last_seen"])

        tokens = generate_tokens_for_user(user)

        return Response(
            {
                "message": "Login successful.",
                "user": UserSerializer(user, context={"request": request}).data,
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Password reset OTP has been sent to your email."},
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Password reset successful. Please login again."},
            status=status.HTTP_200_OK,
        )


class GoogleSignInView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            logger.info(f"Google Sign-In request: {request.data}")
            serializer = GoogleSignInSerializer(data=request.data)

            if not serializer.is_valid():
                logger.warning(f"Serializer errors: {serializer.errors}")
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST,
                )

            result = serializer.save()
            user = result["user"]
            tokens = result["tokens"]

            return Response(
                {
                    "message": "Google sign-in successful.",
                    "user": UserSerializer(user, context={"request": request}).data,
                    "tokens": tokens,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Google Sign-In error: {str(e)}", exc_info=True)
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "user": UserSerializer(request.user, context={"request": request}).data
            },
            status=status.HTTP_200_OK,
        )


class ThemePreferenceView(APIView):
    """Get or update user's theme preference"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get user's theme preference"""
        try:
            theme_preference = request.user.theme_preference
        except ThemePreference.DoesNotExist:
            theme_preference = ThemePreference.objects.create(user=request.user)

        serializer = ThemePreferenceSerializer(theme_preference)
        return Response(
            {
                "message": "Theme preference retrieved successfully.",
                "theme_preference": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def put(self, request):
        """Update user's theme preference"""
        try:
            theme_preference = request.user.theme_preference
        except ThemePreference.DoesNotExist:
            theme_preference = ThemePreference.objects.create(user=request.user)

        serializer = ThemePreferenceSerializer(
            theme_preference,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "message": "Theme preference updated successfully.",
                "theme_preference": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request):
        """Partially update user's theme preference"""
        return self.put(request)