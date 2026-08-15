from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.teams.models import Team, TeamMember, TeamInvitation
from apps.tournaments.models import Game, Tournament, TournamentRegistration, Round, Match
from apps.notifications.models import Notification
from apps.tournaments.services import (
    register_solo_player,
    register_team,
    generate_single_elimination_bracket,
)

User = get_user_model()


class GamesAPITests(TestCase):

    def setUp(self):
        self.client = Client()
        self.game1 = Game.objects.create(name="Valorant", slug="valorant", description="FPS")
        self.game2 = Game.objects.create(name="PUBG Mobile", slug="pubg-mobile", description="BR")

        self.organizer = User.objects.create_user(username="game_org", password="Password123!")
        now = timezone.now()
        Tournament.objects.create(
            name="Val Cup",
            game=self.game1,
            organizer=self.organizer,
            description="Desc",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            max_participants=4,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=3),
            contact_email="val@example.com",
        )

    def test_games_list_api(self):
        url = reverse("api:game_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 2)
        slugs = [g["slug"] for g in data]
        self.assertIn("valorant", slugs)
        self.assertIn("pubg-mobile", slugs)

        # Check tournament count
        val_data = next(g for g in data if g["slug"] == "valorant")
        self.assertEqual(val_data["tournament_count"], 1)
        self.assertIn("image_url", val_data)

    def test_game_detail_api_success(self):
        url = reverse("api:game_detail", kwargs={"slug": "valorant"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["name"], "Valorant")
        self.assertEqual(data["tournament_count"], 1)

    def test_game_detail_api_invalid_slug(self):
        url = reverse("api:game_detail", kwargs={"slug": "non-existent"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_game_tournaments_api(self):
        url = reverse("api:game_tournaments", kwargs={"slug": "valorant"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Val Cup")


class TournamentsAPITests(TestCase):

    def setUp(self):
        self.client = Client()
        self.organizer = User.objects.create_user(username="tourn_org", password="Password123!")
        self.game = Game.objects.create(name="CS2", slug="cs2")

        now = timezone.now()
        self.t1 = Tournament.objects.create(
            name="CS Masters",
            game=self.game,
            organizer=self.organizer,
            description="Major event",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            max_participants=8,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=5),
            contact_email="cs@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )

    def test_tournaments_list_api(self):
        url = reverse("api:tournament_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "CS Masters")
        self.assertEqual(data[0]["game"]["slug"], "cs2")

    def test_tournaments_list_filter_game(self):
        url = reverse("api:tournament_list") + "?game=cs2"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 1)

        url_empty = reverse("api:tournament_list") + "?game=non-existent"
        response_empty = self.client.get(url_empty)
        self.assertEqual(response_empty.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_empty.json()), 0)

    def test_tournaments_list_filter_search(self):
        url = reverse("api:tournament_list") + "?q=Masters"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)

    def test_tournament_detail_api(self):
        url = reverse("api:tournament_detail", kwargs={"pk": self.t1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["name"], "CS Masters")
        self.assertEqual(data["organizer"], "tourn_org")
        self.assertIn("cover_url", data)
        self.assertIn("banner_url", data)

    def test_tournament_detail_api_not_found(self):
        url = reverse("api:tournament_detail", kwargs={"pk": 999999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TeamsAndAutocompleteAPITests(TestCase):

    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(username="team_mgr", password="Password123!")
        self.member = User.objects.create_user(username="team_mem", password="Password123!")
        self.pending = User.objects.create_user(username="team_pending", password="Password123!")
        self.candidate1 = User.objects.create_user(username="candidate_alpha", password="Password123!")
        self.candidate2 = User.objects.create_user(username="CANDIDATE_BETA", password="Password123!")
        self.outsider = User.objects.create_user(username="team_outsider", password="Password123!")

        self.team = Team.objects.create(name="Team Apex", manager=self.manager)
        TeamMember.objects.create(team=self.team, user=self.manager, team_role=TeamMember.TeamRole.MANAGER, is_active=True)
        TeamMember.objects.create(team=self.team, user=self.member, team_role=TeamMember.TeamRole.PLAYER, is_active=True)

        TeamInvitation.objects.create(
            team=self.team,
            sender=self.manager,
            receiver=self.pending,
            status=TeamInvitation.Status.PENDING,
        )

    def test_team_members_api(self):
        url = reverse("api:team_members", kwargs={"slug": self.team.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 2)
        usernames = [m["username"] for m in data]
        self.assertIn("team_mgr", usernames)
        self.assertIn("team_mem", usernames)

    def test_autocomplete_api_unauthenticated_returns_401(self):
        url = reverse("api:user_autocomplete", kwargs={"slug": self.team.slug}) + "?q=candidate"
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_autocomplete_api_non_manager_returns_403(self):
        self.client.login(username="team_outsider", password="Password123!")
        url = reverse("api:user_autocomplete", kwargs={"slug": self.team.slug}) + "?q=candidate"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_autocomplete_api_manager_success_and_exclusions(self):
        self.client.login(username="team_mgr", password="Password123!")
        url = reverse("api:user_autocomplete", kwargs={"slug": self.team.slug}) + "?q=cand"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(isinstance(data, list))

        usernames = [u["username"] for u in data]
        self.assertIn("candidate_alpha", usernames)
        self.assertIn("CANDIDATE_BETA", usernames)

        # Exclusions check
        self.assertNotIn("team_mgr", usernames)
        self.assertNotIn("team_mem", usernames)
        self.assertNotIn("team_pending", usernames)

        # Exposes only id and username
        self.assertEqual(set(data[0].keys()), {"id", "username"})

    def test_autocomplete_api_result_limit_10(self):
        self.client.login(username="team_mgr", password="Password123!")
        for i in range(15):
            User.objects.create_user(username=f"batch_candidate_{i}", password="Password123!")

        url = reverse("api:user_autocomplete", kwargs={"slug": self.team.slug}) + "?q=batch_candidate"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertLessEqual(len(data), 10)


class TournamentRegistrationAPITests(TestCase):

    def setUp(self):
        self.client = Client()
        self.organizer = User.objects.create_user(username="reg_org", password="Password123!")
        self.player1 = User.objects.create_user(username="reg_player1", password="Password123!")
        self.game = Game.objects.create(name="FC 26", slug="fc26")

        now = timezone.now()
        self.solo_tournament = Tournament.objects.create(
            name="Solo Cup",
            game=self.game,
            organizer=self.organizer,
            description="Desc",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.SOLO,
            team_size=1,
            max_participants=2,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=3),
            contact_email="solo@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )

    def test_register_api_unauthenticated_401(self):
        url = reverse("api:tournament_register", kwargs={"pk": self.solo_tournament.pk})
        response = self.client.post(url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_register_api_solo_success(self):
        self.client.login(username="reg_player1", password="Password123!")
        url = reverse("api:tournament_register", kwargs={"pk": self.solo_tournament.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["display_name"], "reg_player1")

    def test_register_api_duplicate_rejected(self):
        self.client.login(username="reg_player1", password="Password123!")
        url = reverse("api:tournament_register", kwargs={"pk": self.solo_tournament.pk})
        response1 = self.client.post(url)
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        response2 = self.client.post(url)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already registered", response2.json()["detail"].lower())

    def test_register_api_closed_rejected(self):
        self.solo_tournament.status = Tournament.Status.REGISTRATION_CLOSED
        self.solo_tournament.save()

        self.client.login(username="reg_player1", password="Password123!")
        url = reverse("api:tournament_register", kwargs={"pk": self.solo_tournament.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("closed", response.json()["detail"].lower())


class LeaderboardAPITests(TestCase):

    def setUp(self):
        self.client = Client()
        self.organizer = User.objects.create_user(username="lead_org", password="Password123!")
        self.game = Game.objects.create(name="Valorant", slug="valorant")
        now = timezone.now()
        self.tournament = Tournament.objects.create(
            name="Leaderboard Cup",
            game=self.game,
            organizer=self.organizer,
            description="Desc",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.SOLO,
            team_size=1,
            max_participants=4,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=3),
            contact_email="lead@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )

        self.solo_user = User.objects.create_user(username="solo_champ", password="Password123!")
        register_solo_player(tournament=self.tournament, user=self.solo_user)

    def test_leaderboard_api_solo_no_internal_team_leakage(self):
        url = reverse("api:tournament_leaderboard", kwargs={"pk": self.tournament.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["tournament_id"], self.tournament.id)
        self.assertEqual(len(data["rankings"]), 1)

        rank_item = data["rankings"][0]
        self.assertEqual(rank_item["name"], "solo_champ")
        self.assertNotIn("__SOLO_", rank_item["name"])


class MatchAPITests(TestCase):

    def setUp(self):
        self.client = Client()
        self.organizer = User.objects.create_user(username="match_org", password="Password123!")
        self.attacker = User.objects.create_user(username="match_attacker", password="Password123!")
        self.game = Game.objects.create(name="Overwatch", slug="overwatch")
        now = timezone.now()
        self.tournament = Tournament.objects.create(
            name="Match Cup",
            game=self.game,
            organizer=self.organizer,
            description="Desc",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.SOLO,
            team_size=1,
            max_participants=2,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=3),
            contact_email="match@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )

        self.u1 = User.objects.create_user(username="player_a", password="Password123!")
        self.u2 = User.objects.create_user(username="player_b", password="Password123!")

        register_solo_player(tournament=self.tournament, user=self.u1)
        register_solo_player(tournament=self.tournament, user=self.u2)

        generate_single_elimination_bracket(tournament=self.tournament)
        self.match = Match.objects.filter(round__tournament=self.tournament).first()

    def test_tournament_matches_api(self):
        url = reverse("api:tournament_matches", kwargs={"pk": self.tournament.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertIn(data[0]["team_one_display"], ["player_a", "player_b"])

    def test_match_detail_api(self):
        url = reverse("api:match_detail", kwargs={"pk": self.match.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["id"], self.match.id)

    def test_match_result_api_unauthorized_attacker_forbidden(self):
        self.client.login(username="match_attacker", password="Password123!")
        url = reverse("api:match_result", kwargs={"pk": self.match.pk})
        response = self.client.post(url, {"team_one_score": 2, "team_two_score": 0}, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_match_result_api_organizer_success(self):
        self.client.login(username="match_org", password="Password123!")
        url = reverse("api:match_result", kwargs={"pk": self.match.pk})
        response = self.client.post(url, {"team_one_score": 2, "team_two_score": 1}, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["status"], Match.Status.COMPLETED)
        self.assertEqual(data["team_one_score"], 2)
        self.assertEqual(data["team_two_score"], 1)


class NotificationAPITests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username="notif_user1", password="Password123!")
        self.user2 = User.objects.create_user(username="notif_user2", password="Password123!")

        self.n1 = Notification.objects.create(recipient=self.user1, title="N1", message="Message 1")
        self.n2 = Notification.objects.create(recipient=self.user1, title="N2", message="Message 2")
        self.n_other = Notification.objects.create(recipient=self.user2, title="Other", message="Other Message")

    def test_notification_list_unauthenticated_401(self):
        response = self.client.get(reverse("api:notification_list"))
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_notification_list_user_isolation(self):
        self.client.login(username="notif_user1", password="Password123!")
        response = self.client.get(reverse("api:notification_list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 2)
        titles = [n["title"] for n in data]
        self.assertIn("N1", titles)
        self.assertNotIn("Other", titles)

    def test_notification_unread_api(self):
        self.client.login(username="notif_user1", password="Password123!")
        response = self.client.get(reverse("api:notification_unread"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["unread_count"], 2)

    def test_notification_mark_read_own_success(self):
        self.client.login(username="notif_user1", password="Password123!")
        url = reverse("api:notification_mark_read", kwargs={"pk": self.n1.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.n1.refresh_from_db()
        self.assertTrue(self.n1.is_read)

    def test_notification_mark_read_cross_user_forbidden_404(self):
        self.client.login(username="notif_user1", password="Password123!")
        url = reverse("api:notification_mark_read", kwargs={"pk": self.n_other.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_notification_mark_read_all(self):
        self.client.login(username="notif_user1", password="Password123!")
        url = reverse("api:notification_mark_read_all")
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["updated_count"], 2)
        self.assertEqual(Notification.objects.filter(recipient=self.user1, is_read=False).count(), 0)


class ProfileAPITests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="profile_user",
            email="profile@example.com",
            password="SecurePassword123!",
            role=User.Role.USER,
        )

    def test_profile_api_unauthenticated_401(self):
        response = self.client.get(reverse("api:user_profile"))
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_profile_api_authenticated_safe_fields(self):
        self.client.login(username="profile_user", password="SecurePassword123!")
        response = self.client.get(reverse("api:user_profile"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data["username"], "profile_user")
        self.assertEqual(data["email"], "profile@example.com")
        self.assertEqual(data["role"], "USER")

        # Verify sensitive fields absent
        self.assertNotIn("password", data)
        self.assertNotIn("password_hash", data)
        self.assertNotIn("secret", data)


class DashboardAPITests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="dash_user", password="Password123!")
        self.team = Team.objects.create(name="Dash Team", manager=self.user)
        TeamMember.objects.create(team=self.team, user=self.user, team_role=TeamMember.TeamRole.MANAGER)

    def test_dashboard_api_unauthenticated_401(self):
        response = self.client.get(reverse("api:dashboard"))
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_dashboard_api_authenticated_metrics(self):
        self.client.login(username="dash_user", password="Password123!")
        response = self.client.get(reverse("api:dashboard"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data["user"]["username"], "dash_user")
        self.assertIn("metrics", data)
        self.assertEqual(data["metrics"]["managed_teams_count"], 1)
        self.assertIn("teams", data)
        self.assertEqual(len(data["teams"]), 1)
        self.assertEqual(data["teams"][0]["name"], "Dash Team")


class TournamentStatisticsAPITests(TestCase):

    def setUp(self):
        self.client = Client()
        self.organizer = User.objects.create_user(username="stat_org", password="Password123!")
        self.game = Game.objects.create(name="Dota 2", slug="dota2")
        now = timezone.now()

        # SOLO tournament
        self.solo_tourney = Tournament.objects.create(
            name="Solo Stat Cup",
            game=self.game,
            organizer=self.organizer,
            description="Desc",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.SOLO,
            team_size=1,
            max_participants=4,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=3),
            contact_email="stat@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )
        self.solo_player = User.objects.create_user(username="solo_stat_player", password="Password123!")
        register_solo_player(tournament=self.solo_tourney, user=self.solo_player)

        # TEAM tournament
        self.team_tourney = Tournament.objects.create(
            name="Team Stat Cup",
            game=self.game,
            organizer=self.organizer,
            description="Desc",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.TEAM,
            team_size=1,
            max_participants=4,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=3),
            contact_email="stat@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )
        self.team_mgr = User.objects.create_user(username="stat_team_mgr", password="Password123!")
        self.team = Team.objects.create(name="Viper Gaming", manager=self.team_mgr)
        TeamMember.objects.create(team=self.team, user=self.team_mgr, team_role=TeamMember.TeamRole.MANAGER)
        register_team(tournament=self.team_tourney, team=self.team, user=self.team_mgr)

    def test_statistics_api_solo_returns_username_no_solo_leakage(self):
        url = reverse("api:tournament_statistics", kwargs={"pk": self.solo_tourney.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["tournament_id"], self.solo_tourney.id)
        self.assertEqual(len(data["rankings"]), 1)
        rank_item = data["rankings"][0]
        self.assertEqual(rank_item["name"], "solo_stat_player")
        self.assertNotIn("__SOLO_", rank_item["name"])

    def test_statistics_api_team_returns_real_team_name(self):
        url = reverse("api:tournament_statistics", kwargs={"pk": self.team_tourney.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data["rankings"]), 1)
        rank_item = data["rankings"][0]
        self.assertEqual(rank_item["name"], "Viper Gaming")

