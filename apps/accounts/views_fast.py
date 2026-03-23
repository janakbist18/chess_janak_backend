"""
Fast and clean login API endpoints
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.utils import timezone

from apps.accounts.serializers import UserSerializer
from apps.accounts.services.fast_auth_service import (
    authenticate_user,
    generate_tokens_for_user,
    user_exists,
)
from apps.accounts.services.fast_otp_service import (
    create_and_send_otp,
    verify_otp,
    resend_otp,
)
from apps.accounts.models import User


class FastLoginView(APIView):
    """
    Fast login endpoint - Returns tokens immediately
    No blocking email operations
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        POST /api/auth/fast-login/
        {
            "email_or_username": "user@email.com",
            "password": "password123"
        }
        """
        email_or_username = request.data.get("email_or_username", "").strip()
        password = request.data.get("password", "").strip()

        # Validate input
        if not email_or_username or not password:
            return Response(
                {"error": "Email/username and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Authenticate user (fast query with prefetch)
        user = authenticate_user(email_or_username, password)

        if not user:
            return Response(
                {"error": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Check if verified
        if not user.is_verified and not user.is_google_account:
            return Response(
                {
                    "error": "Account not verified. Please verify OTP first.",
                    "requires_otp": True,
                    "email": user.email,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not user.is_active:
            return Response(
                {"error": "Account is inactive."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Update last seen
        user.last_seen = timezone.now()
        user.save(update_fields=["last_seen"])

        # Generate tokens
        tokens = generate_tokens_for_user(user)

        return Response(
            {
                "user": UserSerializer(user, context={"request": request}).data,
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )


class FastRegisterView(APIView):
    """
    Fast registration endpoint
    Sends OTP asynchronously (non-blocking)
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        POST /api/auth/fast-register/
        {
            "email": "user@email.com",
            "username": "username",
            "name": "User Name",
            "password": "password123"
        }
        """
        email = request.data.get("email", "").strip().lower()
        username = request.data.get("username", "").strip().lower()
        name = request.data.get("name", "").strip()
        password = request.data.get("password", "").strip()

        # Validate input
        if not all([email, username, name, password]):
            return Response(
                {"error": "All fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(password) < 8:
            return Response(
                {"error": "Password must be at least 8 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if user exists
        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {"error": "Email already registered."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(username__iexact=username).exists():
            return Response(
                {"error": "Username already taken."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create user
        try:
            user = User.objects.create_user(
                email=email,
                username=username,
                name=name,
                password=password,
                is_active=False,  # Inactive until OTP verified
                is_verified=False,
            )

            # Send OTP asynchronously (non-blocking)
            create_and_send_otp(user, purpose="registration")

            return Response(
                {
                    "message": "Registration successful. OTP sent to email.",
                    "email": user.email,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {"error": f"Registration failed: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class FastVerifyOTPView(APIView):
    """
    Fast OTP verification endpoint
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        POST /api/auth/fast-verify-otp/
        {
            "email": "user@email.com",
            "otp_code": "123456"
        }
        """
        email = request.data.get("email", "").strip().lower()
        otp_code = request.data.get("otp_code", "").strip()

        if not email or not otp_code:
            return Response(
                {"error": "Email and OTP are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify OTP (fast query)
        success, user = verify_otp(email, otp_code, purpose="registration")

        if not success:
            return Response(
                {"error": "Invalid or expired OTP."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Mark user as verified and active
        user.is_verified = True
        user.is_active = True
        user.save(update_fields=["is_verified", "is_active"])

        # Generate tokens
        tokens = generate_tokens_for_user(user)

        return Response(
            {
                "message": "Email verified successfully.",
                "user": UserSerializer(user, context={"request": request}).data,
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )


class FastResendOTPView(APIView):
    """
    Fast resend OTP endpoint
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        POST /api/auth/fast-resend-otp/
        {
            "email": "user@email.com"
        }
        """
        email = request.data.get("email", "").strip().lower()

        if not email:
            return Response(
                {"error": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resend OTP (non-blocking)
        if resend_otp(email, purpose="registration"):
            return Response(
                {"message": "OTP sent to your email."},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"error": "Email not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
