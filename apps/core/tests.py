from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from apps.teams.models import Team
from apps.tournaments.models import Game, Tournament
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class CoreHomeViewTests(TestCase):
    """
    Tests for public home view and global statistics calculations.
    """

    def setUp(self):
        self.client = Client()
        self.organizer = User.objects.create_user(username="core_org", password="Password123!")
        self.game = Game.objects.create(name="Overwatch", slug="overwatch")
        self.team = Team.objects.create(name="Overwatch Team", manager=self.organizer)

        now = timezone.now()
        self.tourney = Tournament.objects.create(
            name="Overwatch League",
            game=self.game,
            organizer=self.organizer,
            description="OWL Description",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.TEAM,
            team_size=5,
            max_participants=8,
            registration_start=now - timedelta(days=2),
            registration_end=now - timedelta(days=1),
            start_date=now - timedelta(hours=2),
            end_date=now + timedelta(days=2),
            contact_email="owl@example.com",
            status=Tournament.Status.LIVE,
        )

    def test_home_page_loads_with_correct_stats(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)

        context = response.context
        self.assertEqual(context["featured_tournament"], self.tourney)
        self.assertEqual(context["stats"]["tournaments"], 1)
        self.assertEqual(context["stats"]["teams"], 1)
        self.assertEqual(context["stats"]["games"], 1)


class CoreSearchTests(TestCase):
    """
    Tests for global search view and AJAX search view.
    """

    def setUp(self):
        self.client = Client()
        self.organizer = User.objects.create_user(username="search_user", password="Password123!")
        self.game = Game.objects.create(name="Rocket League", slug="rocket-league")
        self.team = Team.objects.create(name="Rocket Strikers", manager=self.organizer)

        now = timezone.now()
        self.tourney = Tournament.objects.create(
            name="Rocket Masters",
            game=self.game,
            organizer=self.organizer,
            description="High speed RL action",
            rules="Standard",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.TEAM,
            team_size=3,
            max_participants=8,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=5),
            contact_email="rl@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )

    def test_global_search_view(self):
        url = reverse("core:search")
        response = self.client.get(url, {"q": "Rocket"})
        self.assertEqual(response.status_code, 200)

        context = response.context
        self.assertIn(self.tourney, list(context["tournaments"]))
        self.assertIn(self.team, list(context["teams"]))
        self.assertIn(self.game, list(context["games"]))

    def test_search_ajax_view(self):
        url = reverse("core:search_ajax")
        response = self.client.get(url, {"q": "Rocket"})
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data["tournaments"]), 1)
        self.assertEqual(data["tournaments"][0]["name"], "Rocket Masters")
        self.assertEqual(len(data["teams"]), 1)
        self.assertEqual(data["teams"][0]["name"], "Rocket Strikers")
        self.assertEqual(len(data["games"]), 1)
        self.assertEqual(data["games"][0]["name"], "Rocket League")

    def test_search_ajax_short_query_returns_empty(self):
        url = reverse("core:search_ajax")
        response = self.client.get(url, {"q": "R"})
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data["tournaments"]), 0)
        self.assertEqual(len(data["teams"]), 0)
        self.assertEqual(len(data["games"]), 0)
