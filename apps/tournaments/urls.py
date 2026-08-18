from django.urls import path

from .views import (
    TournamentCreateView,
    TournamentDeleteView,
    TournamentDetailView,
    TournamentListView,
    MyTournamentListView,
    TournamentUpdateView,
    TournamentRegisterView,
    TournamentParticipantsView,
    TournamentPublishView,
    TournamentDashboardView,
    CloseRegistrationView,
    GenerateBracketView,
    TournamentBracketView,
    MatchWinnerUpdateView,
    MatchDetailView,
    TournamentMatchesView,
    TournamentStatisticsView,
    TournamentLeaderboardView,
    TournamentNotifyView,
)   

app_name = "tournaments"

urlpatterns = [

    path(
        "",
        TournamentListView.as_view(),
        name="list",
    ),

    path(
        "my/",
        MyTournamentListView.as_view(),
        name="my_list",
    ),

    path(
        "create/",
        TournamentCreateView.as_view(),
        name="create",
    ),

    path(
        "<slug:slug>/notify/",
        TournamentNotifyView.as_view(),
        name="notify",
    ),

    path(
        "<slug:slug>/register/",
        TournamentRegisterView.as_view(),
        name="register",
    ),

    path(
        "<slug:slug>/dashboard/",
        TournamentDashboardView.as_view(),
        name="dashboard",
    ),

    path(
        "<slug:slug>/close-registration/",
        CloseRegistrationView.as_view(),
        name="close_registration",
    ),

    path(
        "<slug:slug>/generate-bracket/",
        GenerateBracketView.as_view(),
        name="generate_bracket",
    ),

    path(
        "<slug:slug>/participants/",
        TournamentParticipantsView.as_view(),
        name="participants",
    ),

    path(
        "<slug:slug>/publish/",
        TournamentPublishView.as_view(),
        name="publish",
    ),

    path(
        "match/<int:match_id>/update/",
        MatchWinnerUpdateView.as_view(),
        name="match_winner_update",
    ),

    path(
        "<slug:slug>/matches/",
        TournamentMatchesView.as_view(),
        name="matches",
    ),

    path(
        "match/<int:pk>/",
        MatchDetailView.as_view(),
        name="match_detail",
    ),

    path(
        "<slug:slug>/bracket/",
        TournamentBracketView.as_view(),
        name="bracket",
    ),

    path(
        "<slug:slug>/statistics/",
        TournamentStatisticsView.as_view(),
        name="statistics",
    ),

    path(
        "<slug:slug>/leaderboard/",
        TournamentLeaderboardView.as_view(),
        name="leaderboard",
    ),


    path(
        "<slug:slug>/",
        TournamentDetailView.as_view(),
        name="detail",
    ),
    
    

    path(
        "<slug:slug>/edit/",
        TournamentUpdateView.as_view(),
        name="edit",
    ),

    path(
        "<slug:slug>/delete/",
        TournamentDeleteView.as_view(),
        name="delete",
    ),
]