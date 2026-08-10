from django.urls import path

from .views import (
    NotificationListView,
    AcceptInvitationView,
    RejectInvitationView,
    MarkAsReadView,
    MarkAllAsReadView,
)

app_name = "notifications"

urlpatterns = [
    path(
        "",
        NotificationListView.as_view(),
        name="list",
    ),

    path(
        "<int:pk>/read/",
        MarkAsReadView.as_view(),
        name="mark_as_read",
    ),

    path(
        "read-all/",
        MarkAllAsReadView.as_view(),
        name="mark_all_read",
    ),

    path(
        "<int:pk>/accept/",
        AcceptInvitationView.as_view(),
        name="accept",
    ),

    path(
        "<int:pk>/accept-invitation/",
        AcceptInvitationView.as_view(),
        name="accept_invitation",
    ),

    path(
        "<int:pk>/reject/",
        RejectInvitationView.as_view(),
        name="reject",
    ),

    path(
        "<int:pk>/reject-invitation/",
        RejectInvitationView.as_view(),
        name="reject_invitation",
    ),
]