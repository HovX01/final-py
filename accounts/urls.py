from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    EmailLoginView,
    ForgotPasswordDoneView,
    ForgotPasswordView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    profile,
    register,
    verify_email,
)

app_name = "accounts"

urlpatterns = [
    path("register/", register, name="register"),
    path("login/", EmailLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("verify/", verify_email, name="verify_email"),
    path("password-reset/", ForgotPasswordView.as_view(), name="password_reset"),
    path("password-reset/done/", ForgotPasswordDoneView.as_view(), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("reset/done/", PasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path("profile/", profile, name="profile"),
]
