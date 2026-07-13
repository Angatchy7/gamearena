from django.urls import path

from .views import (
    TournamentCreateView,
    TournamentDeleteView,
    TournamentDetailView,
    TournamentListView,
    TournamentUpdateView,
)

app_name = "tournaments"

urlpatterns = [

    path(
        "",
        TournamentListView.as_view(),
        name="list",
    ),

    path(
        "create/",
        TournamentCreateView.as_view(),
        name="create",
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