from django.urls import path

from apps.accounts.views_device import (
    HealthCheckView,
    GetDeviceIDView,
    CurrentUserView,
    AuthStatusView,
)

# Legacy endpoints are commented out - use device_id based authentication instead
# If you need backward compatibility with old authentication, uncomment these:
# from rest_framework_simplejwt.views import TokenRefreshView
# from apps.accounts.views import (
#     ForgotPasswordView,
#     GoogleSignInView,
#     LoginView,
#     MeView,
#     RegisterView,
#     ResendRegistrationOTPView,
#     ResetPasswordView,
#     ThemePreferenceView,
#     VerifyRegistrationOTPView,
# )
# from apps.accounts.views_fast import (
#     FastLoginView,
#     FastRegisterView,
#     FastResendOTPView,
#     FastVerifyOTPView,
# )
# from apps.accounts.views_google_callback import GoogleCallbackView

urlpatterns = [
    # Health & Device ID endpoints
    path("", HealthCheckView.as_view(), name="accounts-health"),
    path("device-id/", GetDeviceIDView.as_view(), name="get-device-id"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("status/", AuthStatusView.as_view(), name="auth-status"),

    # Legacy authentication endpoints (disabled - no longer needed)
    # Uncomment below if you need backward compatibility with email/password authentication
    #
    # path("register/", RegisterView.as_view(), name="register"),
    # path("verify-otp/", VerifyRegistrationOTPView.as_view(), name="verify-otp"),
    # path("resend-otp/", ResendRegistrationOTPView.as_view(), name="resend-otp"),
    # path("login/", LoginView.as_view(), name="login"),
    # path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    # path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    # path("google/", GoogleSignInView.as_view(), name="google-signin"),
    # path("google/callback/", GoogleCallbackView.as_view(), name="google-callback"),
    # path("fast-register/", FastRegisterView.as_view(), name="fast-register"),
    # path("fast-verify-otp/", FastVerifyOTPView.as_view(), name="fast-verify-otp"),
    # path("fast-resend-otp/", FastResendOTPView.as_view(), name="fast-resend-otp"),
    # path("fast-login/", FastLoginView.as_view(), name="fast-login"),
    # path("theme-preference/", ThemePreferenceView.as_view(), name="theme-preference"),
    # path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]