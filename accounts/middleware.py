from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect


class DisabledUserMiddleware:
    """Logs out and blocks disabled users from accessing the site."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and getattr(request.user, "is_disabled", False):
            logout(request)
            messages.error(request, "Your account has been disabled.")
            return redirect("accounts:login")
        return self.get_response(request)
