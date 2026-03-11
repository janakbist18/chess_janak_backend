from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.views import (
    ForgotPasswordView,
    GoogleSignInView,
    HealthCheckView,
    LoginView,
    MeView,
    RegisterView,
    ResendRegistrationOTPView,
    ResetPasswordView,
    VerifyRegistrationOTPView,
)

urlpatterns = [
    path("", HealthCheckView.as_view(), name="accounts-health"),
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-otp/", VerifyRegistrationOTPView.as_view(), name="verify-otp"),
    path("resend-otp/", ResendRegistrationOTPView.as_view(), name="resend-otp"),
    path("login/", LoginView.as_view(), name="login"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    path("google/", GoogleSignInView.as_view(), name="google-signin"),
    path("me/", MeView.as_view(), name="me"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]