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
