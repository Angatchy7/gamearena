from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.notifications.models import Notification
from apps.notifications.services import (
    send_notification,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    get_unread_count,
)
from apps.teams.models import Team, TeamInvitation

User = get_user_model()


class NotificationServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="player1",
            email="player1@example.com",
            password="password123",
        )

    def test_send_notification(self):
        notification = send_notification(
            recipient=self.user,
            title="Match Alert",
            message="Your match starts in 15 minutes.",
            notification_type=Notification.Type.MATCH,
        )
        self.assertEqual(notification.recipient, self.user)
        self.assertFalse(notification.is_read)
        self.assertEqual(get_unread_count(user=self.user), 1)

    def test_mark_notification_as_read(self):
        notification = send_notification(
            recipient=self.user,
            title="System Alert",
            message="Welcome to GameArena!",
        )
        mark_notification_as_read(notification=notification)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertEqual(get_unread_count(user=self.user), 0)

    def test_mark_all_notifications_as_read(self):
        send_notification(recipient=self.user, title="N1", message="M1")
        send_notification(recipient=self.user, title="N2", message="M2")
        self.assertEqual(get_unread_count(user=self.user), 2)

        mark_all_notifications_as_read(user=self.user)
        self.assertEqual(get_unread_count(user=self.user), 0)


class NotificationViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="player2",
            email="player2@example.com",
            password="password123",
        )
        self.client.login(username="player2", password="password123")

    def test_notification_list_view(self):
        send_notification(recipient=self.user, title="Notice 1", message="Message 1")
        response = self.client.get(reverse("notifications:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Notice 1")
        self.assertEqual(response.context["unread_count"], 1)

    def test_mark_as_read_view(self):
        n = send_notification(recipient=self.user, title="Notice 1", message="Message 1")
        response = self.client.post(reverse("notifications:mark_as_read", kwargs={"pk": n.pk}))
        self.assertRedirects(response, reverse("notifications:list"))
        n.refresh_from_db()
        self.assertTrue(n.is_read)

    def test_mark_all_read_view(self):
        send_notification(recipient=self.user, title="N1", message="M1")
        send_notification(recipient=self.user, title="N2", message="M2")
        response = self.client.post(reverse("notifications:mark_all_read"))
        self.assertRedirects(response, reverse("notifications:list"))
        self.assertEqual(get_unread_count(user=self.user), 0)
