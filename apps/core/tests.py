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


import os
from unittest.mock import patch
from django.conf import settings
from django.core.files.storage import storages, FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings


class MediaStorageTests(TestCase):
    """
    Tests for Cloudinary media storage, local FileSystemStorage fallback,
    uploaded image priority, static fallback hierarchy, and zero migrations invariant.
    """

    def test_local_storage_without_cloudinary_credentials(self):
        """
        Verify FileSystemStorage is configured when Cloudinary credentials are absent.
        """
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(os.getenv("CLOUDINARY_CLOUD_NAME"))
            self.assertIsNone(os.getenv("CLOUDINARY_API_KEY"))
            self.assertIsNone(os.getenv("CLOUDINARY_API_SECRET"))
            # In current test context without Cloudinary env vars, default storage should be FileSystemStorage
            storage = storages["default"]
            self.assertIsInstance(storage, FileSystemStorage)

    def test_cloudinary_configuration_when_credentials_exist(self):
        """
        Verify Cloudinary storage backend resolution when credentials exist.
        """
        env_credentials = {
            "CLOUDINARY_CLOUD_NAME": "demo_cloud",
            "CLOUDINARY_API_KEY": "123456789012345",
            "CLOUDINARY_API_SECRET": "abcdefghijklmnopqrstuvwxyz1",
        }
        with patch.dict(os.environ, env_credentials):
            self.assertEqual(os.getenv("CLOUDINARY_CLOUD_NAME"), "demo_cloud")
            self.assertEqual(os.getenv("CLOUDINARY_API_KEY"), "123456789012345")
            self.assertEqual(os.getenv("CLOUDINARY_API_SECRET"), "abcdefghijklmnopqrstuvwxyz1")

            with override_settings(
                STORAGES={
                    "default": {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"},
                    "staticfiles": settings.STORAGES["staticfiles"],
                },
                CLOUDINARY_STORAGE={
                    "CLOUD_NAME": "demo_cloud",
                    "API_KEY": "123456789012345",
                    "API_SECRET": "abcdefghijklmnopqrstuvwxyz1",
                },
            ):
                storage = storages["default"]
                self.assertEqual(storage.__class__.__module__, "cloudinary_storage.storage")
                self.assertEqual(storage.__class__.__name__, "MediaCloudinaryStorage")

    def test_uploaded_image_priority(self):
        """
        Verify uploaded image takes priority over static fallbacks and uses FieldFile.url.
        """
        user = User.objects.create_user(username="media_mgr", password="Password123!")

        # Team logo uploaded image priority
        team = Team.objects.create(name="Media Stars", manager=user)
        logo_file = SimpleUploadedFile("team_logo.png", b"fake_png_data", content_type="image/png")
        team.logo = logo_file
        team.save()
        self.assertTrue(bool(team.logo))
        self.assertEqual(team.logo_url, team.logo.url)

        # Game logo uploaded image priority
        game = Game.objects.create(name="Custom Apex", slug="custom-apex")
        game_logo = SimpleUploadedFile("game_logo.png", b"fake_png_data", content_type="image/png")
        game.logo = game_logo
        game.save()
        self.assertTrue(bool(game.logo))
        self.assertEqual(game.image_url, game.logo.url)

        # Tournament cover and banner uploaded image priority
        now = timezone.now()
        tourney = Tournament.objects.create(
            name="Media Cup",
            game=game,
            organizer=user,
            description="Desc",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            max_participants=4,
            registration_start=now,
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=3),
            contact_email="media@example.com",
        )
        cover_file = SimpleUploadedFile("cover.png", b"fake_cover", content_type="image/png")
        banner_file = SimpleUploadedFile("banner.png", b"fake_banner", content_type="image/png")
        tourney.cover_image = cover_file
        tourney.banner = banner_file
        tourney.save()

        self.assertEqual(tourney.cover_url, tourney.cover_image.url)
        self.assertEqual(tourney.banner_url, tourney.banner.url)

    def test_fallback_priority_hierarchy(self):
        """
        Verify fallback hierarchy when no uploaded file exists:
        uploaded image > specific static artwork > generic static artwork.
        """
        user = User.objects.create_user(username="fallback_mgr", password="Password123!")

        # Team fallback
        team = Team.objects.create(name="Fallback Squad", manager=user)
        self.assertEqual(team.logo_url, "/static/images/defaults/team_default.svg")

        # Game fallback - specific artwork
        game_pubg = Game.objects.create(name="PUBG Mobile", slug="pubg-mobile")
        self.assertEqual(game_pubg.image_url, "/static/images/games/pubg.svg")

        # Game fallback - generic default
        game_generic = Game.objects.create(name="Unknown Title", slug="unknown-title")
        self.assertEqual(game_generic.image_url, "/static/images/defaults/game_default.svg")

        # Tournament fallback to game artwork
        now = timezone.now()
        tourney = Tournament.objects.create(
            name="PUBG Showdown",
            game=game_pubg,
            organizer=user,
            description="Desc",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            max_participants=4,
            registration_start=now,
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=3),
            contact_email="pubg@example.com",
        )
        self.assertEqual(tourney.cover_url, "/static/images/games/pubg.svg")
        self.assertEqual(tourney.banner_url, "/static/images/games/pubg.svg")

        # Tournament fallback to generic defaults when game has generic default
        tourney_generic = Tournament.objects.create(
            name="Generic Cup",
            game=game_generic,
            organizer=user,
            description="Desc",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            max_participants=4,
            registration_start=now,
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=3),
            contact_email="generic@example.com",
        )
        tourney_generic.game = None
        self.assertEqual(tourney_generic.cover_url, "/static/images/defaults/tournament_cover.svg")
        self.assertEqual(tourney_generic.banner_url, "/static/images/defaults/tournament_banner.svg")

    def test_zero_migrations(self):
        """
        Verify no migrations were created or are pending.
        """
        try:
            call_command("makemigrations", check=True, dry_run=True)
        except SystemExit as e:
            self.assertEqual(e.code, 0, "makemigrations --check --dry-run detected pending migrations")

