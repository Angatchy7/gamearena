import json
import os
import secrets
from django.contrib.auth import get_user_model
from django.contrib.auth import views as auth_views
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .forms import UserRegistrationForm
from .services import get_player_profile

User = get_user_model()


class RegisterView(View):
    """
    Handles user registration.
    GET  — renders the blank registration form.
    POST — validates and saves the new user, then redirects to login.
    """

    template_name = 'accounts/register.html'

    def get(self, request):
        form = UserRegistrationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('accounts:login')
        return render(request, self.template_name, {'form': form})


class PlayerProfileView(View):
    """
    Public player profile view displaying user info, teams, matches, stats, and achievements.
    """

    template_name = "accounts/profile.html"

    def get(self, request, username):
        user = get_object_or_404(User, username=username)
        context = get_player_profile(user=user)
        return render(request, self.template_name, context)


@method_decorator(csrf_exempt, name="dispatch")
class SuperuserSetupView(View):
    """
    Temporary JSON endpoint for initial production superuser creation on Render.
    Requires environment variable SETUP_ADMIN_TOKEN to be set.
    """

    def post(self, request):
        env_token = os.getenv("SETUP_ADMIN_TOKEN", "").strip()
        if not env_token:
            return JsonResponse({"error": "Setup disabled."}, status=404)

        try:
            data = json.loads(request.body.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("JSON body must be an object.")
        except Exception:
            return JsonResponse({"error": "Invalid JSON body."}, status=400)

        token = str(data.get("token") or "").strip()
        username = str(data.get("username") or "").strip()
        email = str(data.get("email") or "").strip()
        password = str(data.get("password") or "").strip()

        if not token or not secrets.compare_digest(token, env_token):
            return JsonResponse({"error": "Invalid setup token."}, status=403)

        if not username or not password:
            return JsonResponse({"error": "Username and password are required."}, status=400)

        if User.objects.filter(username__iexact=username).exists():
            return JsonResponse({"error": f"User with username '{username}' already exists."}, status=400)

        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        user.role = User.Role.ADMIN
        user.save()

        return JsonResponse({
            "success": True,
            "message": f"Superuser '{user.username}' successfully created.",
            "username": user.username,
            "email": user.email,
        })
