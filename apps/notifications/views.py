from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView

from .models import Notification
from apps.teams.models import TeamInvitation
from apps.teams.services import (
    accept_team_invitation,
    reject_team_invitation,
)


class NotificationListView(LoginRequiredMixin, ListView):

    model = Notification

    template_name = "notifications/list.html"

    context_object_name = "notifications"

    def get_queryset(self):

        return (
            Notification.objects.filter(
                recipient=self.request.user,
            )
            .select_related(
                "team_invitation",
            )
            .order_by("-created_at")
        )


class AcceptInvitationView(LoginRequiredMixin, View):

    def post(self, request, pk):

        notification = get_object_or_404(
            Notification,
            pk=pk,
            recipient=request.user,
        )

        invitation = notification.team_invitation

        if invitation:
            accept_team_invitation(
                invitation,
            )

        return redirect(
            "notifications:list",
        )


class RejectInvitationView(LoginRequiredMixin, View):

    def post(self, request, pk):

        notification = get_object_or_404(
            Notification,
            pk=pk,
            recipient=request.user,
        )

        invitation = notification.team_invitation

        if invitation:
            reject_team_invitation(
                invitation,
            )

        return redirect(
            "notifications:list",
        )