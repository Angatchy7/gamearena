from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):

    model = Notification

    template_name = "notifications/list.html"

    context_object_name = "notifications"

    def get_queryset(self):

        return (
            Notification.objects.filter(
                recipient=self.request.user,
            )
            .order_by("-created_at")
        )