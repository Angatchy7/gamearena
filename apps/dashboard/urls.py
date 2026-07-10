from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_home, name="home"),
    path("admin/", views.admin_dashboard, name="admin_dashboard"),
    path("captain/", views.captain_dashboard, name="captain_dashboard"),
    path("player/", views.player_dashboard, name="player_dashboard"),
]