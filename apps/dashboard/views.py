from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.core.decorators import admin_required


@login_required
def dashboard_home(request):
    """
    Main dashboard for all users.
    """
    return render(request, "dashboard/home.html")


@login_required
@admin_required
def admin_dashboard(request):
    """
    Website administrator dashboard.
    """
    return render(request, "dashboard/admin.html")