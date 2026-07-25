from django.urls import path

from .views import (
    NotificationListView,
    AcceptInvitationView,
    RejectInvitationView,
)

app_name = "notifications"

urlpatterns = [
    path(
        "",
        NotificationListView.as_view(),
        name="list",
    ),

    path(
        "<int:pk>/accept/",
        AcceptInvitationView.as_view(),
        name="accept",
    ),

    path(
        "<int:pk>/reject/",
        RejectInvitationView.as_view(),
        name="reject",
    ),
]