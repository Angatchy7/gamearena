from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.accounts.models import User
from apps.core.decorators import (
    admin_required,
    captain_required,
    player_required,
)


@login_required
def dashboard_home(request):
    """
    Redirect authenticated users to their
    role-specific dashboard.
    """

    if request.user.role == User.Role.ADMIN:
        return redirect("dashboard:admin_dashboard")

    elif request.user.role == User.Role.CAPTAIN:
        return redirect("dashboard:captain_dashboard")

    return redirect("dashboard:player_dashboard")


@login_required
@admin_required
def admin_dashboard(request):
    return render(request, "dashboard/admin.html")


@login_required
@captain_required
def captain_dashboard(request):
    return render(request, "dashboard/captain.html")


@login_required
@player_required
def player_dashboard(request):
    return render(request, "dashboard/player.html")