from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView

from .models import Notification
# pyrefly: ignore [missing-import]
from apps.teams.models import TeamInvitation
# pyrefly: ignore [missing-import]
from apps.teams.services import (
    accept_team_invitation,
    reject_team_invitation,
)


from .services import (
    mark_notification_as_read,
    mark_all_notifications_as_read,
)


class NotificationListView(LoginRequiredMixin, ListView):

    model = Notification

    template_name = "notifications/list.html"

    context_object_name = "notifications"

    paginate_by = 10

    def get_queryset(self):
        qs = (
            Notification.objects.filter(
                recipient=self.request.user,
            )
            .select_related(
                "team_invitation",
            )
            .order_by("-created_at")
        )

        filter_type = self.request.GET.get("filter", "all")
        if filter_type == "unread":
            qs = qs.filter(is_read=False)
        elif filter_type == "read":
            qs = qs.filter(is_read=True)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_notifications = Notification.objects.filter(
            recipient=self.request.user,
        )

        context["unread_count"] = user_notifications.filter(
            is_read=False,
        ).count()
        context["read_count"] = user_notifications.filter(
            is_read=True,
        ).count()
        context["total_count"] = user_notifications.count()
        context["current_filter"] = self.request.GET.get("filter", "all")
        return context


class MarkAsReadView(LoginRequiredMixin, View):
    """
    Marks a single notification as read.
    """

    def post(self, request, pk):
        notification = get_object_or_404(
            Notification,
            pk=pk,
            recipient=request.user,
        )

        mark_notification_as_read(
            notification=notification,
        )

        redirect_url = request.META.get("HTTP_REFERER")
        if redirect_url:
            return redirect(redirect_url)
        return redirect("notifications:list")


class MarkAllAsReadView(LoginRequiredMixin, View):
    """
    Marks all notifications for the logged-in user as read.
    """

    def post(self, request):
        mark_all_notifications_as_read(
            user=request.user,
        )

        redirect_url = request.META.get("HTTP_REFERER")
        if redirect_url:
            return redirect(redirect_url)
        return redirect("notifications:list")


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

        redirect_url = request.META.get("HTTP_REFERER")
        if redirect_url:
            return redirect(redirect_url)
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

        redirect_url = request.META.get("HTTP_REFERER")
        if redirect_url:
            return redirect(redirect_url)
        return redirect(
            "notifications:list",
        )
