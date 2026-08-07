from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, render
from django.views import View

from .forms import UserRegistrationForm


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


from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .services import get_player_profile

User = get_user_model()


class PlayerProfileView(View):
    """
    Public player profile view displaying user info, teams, matches, stats, and achievements.
    """

    template_name = "accounts/profile.html"

    def get(self, request, username):
        user = get_object_or_404(User, username=username)
        context = get_player_profile(user=user)
        return render(request, self.template_name, context)

