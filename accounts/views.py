import random
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.contrib.auth.hashers import make_password

from .forms import EmailAuthenticationForm, UserRegistrationForm, VerificationCodeForm
from .models import PendingRegistration, VerificationCode

User = get_user_model()


class EmailLoginView(auth_views.LoginView):
    authentication_form = EmailAuthenticationForm
    template_name = "accounts/login.html"

    def form_valid(self, form):
        user = form.get_user()
        if getattr(user, "is_disabled", False):
            logout(self.request)
            messages.error(self.request, "Your account has been disabled. Contact support.")
            return redirect("accounts:login")
        if not getattr(user, "is_verified", True):
            logout(self.request)
            messages.error(self.request, "Please verify your email before logging in.")
            return redirect("accounts:login")
        return super().form_valid(form)


def register(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            if User.objects.filter(email=email).exists():
                form.add_error("email", "An account with this email already exists.")
            else:
                PendingRegistration.objects.filter(email=email).delete()
                pending = PendingRegistration.objects.create(
                    email=email,
                    first_name=form.cleaned_data.get("first_name", ""),
                    last_name=form.cleaned_data.get("last_name", ""),
                    password=make_password(form.cleaned_data["password1"]),
                    code=_generate_code(),
                    expires_at=timezone.now() + timedelta(minutes=10),
                )
                _send_verification_code(pending)
                request.session["pending_registration_id"] = pending.id
                messages.success(request, "Registration started. Enter the verification code we emailed you.")
                return redirect("accounts:verify_email")
    else:
        form = UserRegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


def _generate_code():
    return f"{random.randint(0, 999999):06d}"


def _send_verification_code(pending):
    code = pending.code
    send_mail(
        subject="Your verification code",
        message=f"Your verification code is: {code}\n\nIt expires in 10 minutes.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[pending.email],
        fail_silently=False,
    )


def verify_email(request):
    pending_id = request.session.get("pending_registration_id")
    if not pending_id:
        messages.error(request, "No verification in progress. Please register first.")
        return redirect("accounts:register")
    pending = get_object_or_404(PendingRegistration, pk=pending_id)

    if request.method == "POST":
        form = VerificationCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"]
            if pending.code == code and pending.is_valid:
                if User.objects.filter(email=pending.email).exists():
                    messages.error(request, "Account already exists. Please log in.")
                    request.session.pop("pending_registration_id", None)
                    pending.delete()
                    return redirect("accounts:login")
                user = User(
                    email=pending.email,
                    first_name=pending.first_name,
                    last_name=pending.last_name,
                    user_type=User.BASIC,
                    email_verified_at=timezone.now(),
                )
                user.password = pending.password
                user.save()
                pending.delete()
                request.session.pop("pending_registration_id", None)
                login(request, user)
                messages.success(request, "Email verified. You are now logged in.")
                return redirect("home")
            messages.error(request, "Invalid or expired code.")
    else:
        form = VerificationCodeForm()

    return render(request, "accounts/verify_code.html", {"form": form, "email": pending.email})


class ForgotPasswordView(auth_views.PasswordResetView):
    email_template_name = "accounts/emails/password_reset_email.txt"
    subject_template_name = "accounts/emails/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")
    template_name = "accounts/password_reset.html"


class ForgotPasswordDoneView(auth_views.PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    success_url = reverse_lazy("accounts:password_reset_complete")
    template_name = "accounts/password_reset_confirm.html"


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


@login_required
def profile(request):
    return render(request, "accounts/profile.html")

# Create your views here.
