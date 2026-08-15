from django.urls import path

from .views import (
    MyTeamsView,
    JoinedTeamsView,
    CreateTeamView,
    TeamDetailView,
    TeamUpdateView,
    TeamInviteView,
    RemoveTeamMemberView,
    UserAutocompleteView,
)

app_name = "teams"

urlpatterns = [
    path("", MyTeamsView.as_view(), name="list"),
    path("joined/", JoinedTeamsView.as_view(), name="joined"),
    path("create/", CreateTeamView.as_view(), name="create"),
    path("<slug:slug>/", TeamDetailView.as_view(), name="detail"),
    path("<slug:slug>/edit/", TeamUpdateView.as_view(), name="edit"),
    path("<slug:slug>/invite/", TeamInviteView.as_view(), name="invite"),
    path("<slug:slug>/invite/autocomplete/", UserAutocompleteView.as_view(), name="user_autocomplete"),
    path("<slug:slug>/remove-member/<int:member_id>/", RemoveTeamMemberView.as_view(), name="remove_member"),
]