from django.urls import path

from .views import (
    TeamListView,
    CreateTeamView,
    TeamDetailView,
    TeamUpdateView,
    TeamInviteView,
    UserAutocompleteView,
)

app_name = "teams"

urlpatterns = [
    path("", TeamListView.as_view(), name="list"),
    path("create/", CreateTeamView.as_view(), name="create"),
    path("<slug:slug>/", TeamDetailView.as_view(), name="detail"),
    path("<slug:slug>/edit/", TeamUpdateView.as_view(), name="edit"),
    path("<slug:slug>/invite/", TeamInviteView.as_view(), name="invite"),
    path("<slug:slug>/invite/autocomplete/", UserAutocompleteView.as_view(), name="user_autocomplete"),
]