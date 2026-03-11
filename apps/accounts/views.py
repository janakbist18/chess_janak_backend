from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import (
    ForgotPasswordSerializer,
    GoogleSignInSerializer,
    LoginSerializer,
    RegisterSerializer,
    ResendRegistrationOTPSerializer,
    ResetPasswordSerializer,
    UserSerializer,
    VerifyRegistrationOTPSerializer,
)
from apps.accounts.services.auth_service import generate_tokens_for_user


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
        serializer = GoogleSignInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
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


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "user": UserSerializer(request.user, context={"request": request}).data
            },
            status=status.HTTP_200_OK,
        )