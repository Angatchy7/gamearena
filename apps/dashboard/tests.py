from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from apps.teams.models import Team, TeamMember
from apps.tournaments.models import Game, Tournament, TournamentRegistration
from apps.notifications.services import send_notification
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class DashboardViewTests(TestCase):
    """
    Tests for dashboard_home and admin_dashboard views.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="dash_user", password="Password123!")
        self.admin = User.objects.create_user(username="dash_admin", password="Password123!", role=User.Role.ADMIN)

        self.game = Game.objects.create(name="Valorant")
        self.team = Team.objects.create(name="Dash Team", manager=self.user)
        TeamMember.objects.create(team=self.team, user=self.user)

        now = timezone.now()
        self.tourney = Tournament.objects.create(
            name="Dash Championship",
            game=self.game,
            organizer=self.user,
            description="Desc",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.TEAM,
            team_size=5,
            max_participants=4,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=5),
            contact_email="dash@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )
        TournamentRegistration.objects.create(tournament=self.tourney, team=self.team, registered_by=self.user)
        send_notification(recipient=self.user, title="Welcome", message="Hello")

    def test_dashboard_home_unauthenticated_redirects(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_dashboard_home_authenticated(self):
        self.client.login(username="dash_user", password="Password123!")
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)

        context = response.context
        self.assertEqual(len(context["user_teams"]), 1)
        self.assertEqual(context["user_teams"][0], self.team)
        self.assertEqual(context["all_organized_count"], 1)
        self.assertEqual(context["joined_tournaments_count"], 1)
        self.assertEqual(context["unread_notifications_count"], 1)

    def test_admin_dashboard_role_permission(self):
        # User role -> 403 Forbidden
        self.client.login(username="dash_user", password="Password123!")
        response_user = self.client.get(reverse("dashboard:admin"))
        self.assertEqual(response_user.status_code, 403)

        # Admin role -> 200 OK
        self.client.login(username="dash_admin", password="Password123!")
        response_admin = self.client.get(reverse("dashboard:admin"))
        self.assertEqual(response_admin.status_code, 200)
