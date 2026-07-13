from django.urls import path

from .views import (
    CreateTeamView,
    TeamDetailView,
    TeamUpdateView,
)

app_name = "teams"

urlpatterns = [
    path(
        "create/",
        CreateTeamView.as_view(),
        name="create",
    ),

    path(
        "<slug:slug>/",
        TeamDetailView.as_view(),
        name="detail",
    ),

    path(
        "<slug:slug>/edit/",
        TeamUpdateView.as_view(),
        name="edit",
    ),

    
]