from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from apps.teams.models import Team, TeamMember
from apps.tournaments.models import Game, Tournament, TournamentRegistration
from apps.notifications.services import send_notification
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


from apps.tournaments.services import register_solo_player, register_team


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

    def test_solo_registration_visibility_and_joined_tournaments(self):
        # TEST 1: Create a SOLO tournament, register Player1 individually.
        player1 = User.objects.create_user(username="solo_vis_p1", password="Password123!")
        now = timezone.now()
        solo_tourney = Tournament.objects.create(
            name="Solo Visibility Cup",
            game=self.game,
            organizer=self.user,
            description="Solo Desc",
            rules="Solo Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.SOLO,
            team_size=1,
            max_participants=4,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=5),
            contact_email="solo@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )

        res = register_solo_player(tournament=solo_tourney, user=player1)
        self.assertTrue(res["success"])
        reg = TournamentRegistration.objects.get(tournament=solo_tourney, user=player1)
        self.assertEqual(reg.user, player1)

        self.client.login(username="solo_vis_p1", password="Password123!")
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)
        context = response.context

        # Tournament appears in Joined Tournaments
        self.assertEqual(context["joined_tournaments_count"], 1)
        joined_t_ids = [r.tournament.id for r in context["joined_registrations"]]
        self.assertIn(solo_tourney.id, joined_t_ids)

        # Internal solo team does NOT appear in My Teams
        self.assertEqual(len(context["user_teams"]), 0)
        self.assertEqual(len(context["managed_teams"]), 0)

    def test_real_team_appears_in_my_teams_and_joined_tournaments(self):
        # TEST 2: Create real TeamAlpha managed by Player1, register TeamAlpha in TEAM tournament.
        player1 = User.objects.create_user(username="real_team_p1", password="Password123!")
        team_alpha = Team.objects.create(name="TeamAlpha", manager=player1)
        TeamMember.objects.create(team=team_alpha, user=player1, team_role=TeamMember.TeamRole.MANAGER, is_active=True)
        # Add additional player for team_size requirement
        p2 = User.objects.create_user(username="real_team_p2", password="Password123!")
        TeamMember.objects.create(team=team_alpha, user=p2, team_role=TeamMember.TeamRole.PLAYER, is_active=True)

        now = timezone.now()
        team_tourney = Tournament.objects.create(
            name="Team Alpha Cup",
            game=self.game,
            organizer=self.user,
            description="Team Desc",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.TEAM,
            team_size=2,
            max_participants=4,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=5),
            contact_email="team@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )

        res = register_team(tournament=team_tourney, team=team_alpha, user=player1)
        self.assertTrue(res["success"])

        self.client.login(username="real_team_p1", password="Password123!")
        response = self.client.get(reverse("dashboard:home"))
        context = response.context

        # TeamAlpha appears in My Teams
        self.assertEqual(len(context["user_teams"]), 1)
        self.assertEqual(context["user_teams"][0], team_alpha)

        # TEAM tournament appears in Joined Tournaments
        self.assertEqual(context["joined_tournaments_count"], 1)

    def test_player_with_both_solo_and_team_tournaments(self):
        # TEST 3: Player1 has SOLO Tournament A and TEAM Tournament B.
        player1 = User.objects.create_user(username="both_p1", password="Password123!")
        team_beta = Team.objects.create(name="TeamBeta", manager=player1)
        TeamMember.objects.create(team=team_beta, user=player1, team_role=TeamMember.TeamRole.MANAGER, is_active=True)
        p2 = User.objects.create_user(username="both_p2", password="Password123!")
        TeamMember.objects.create(team=team_beta, user=p2, team_role=TeamMember.TeamRole.PLAYER, is_active=True)

        now = timezone.now()
        solo_t = Tournament.objects.create(
            name="Solo Tourney A",
            game=self.game,
            organizer=self.user,
            description="Solo",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.SOLO,
            team_size=1,
            max_participants=4,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=5),
            contact_email="s@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )

        team_t = Tournament.objects.create(
            name="Team Tourney B",
            game=self.game,
            organizer=self.user,
            description="Team",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.TEAM,
            team_size=2,
            max_participants=4,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=5),
            contact_email="t@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )

        register_solo_player(tournament=solo_t, user=player1)
        register_team(tournament=team_t, team=team_beta, user=player1)

        self.client.login(username="both_p1", password="Password123!")
        response = self.client.get(reverse("dashboard:home"))
        context = response.context

        # Joined Tournaments contains both exactly once
        self.assertEqual(context["joined_tournaments_count"], 2)
        # My Teams contains only TeamBeta, NOT internal solo team
        self.assertEqual(len(context["user_teams"]), 1)
        self.assertEqual(context["user_teams"][0], team_beta)

    def test_multiple_solo_tournaments_in_joined_events(self):
        # TEST 4: Player1 registers for multiple SOLO tournaments.
        player1 = User.objects.create_user(username="multi_solo_p1", password="Password123!")
        now = timezone.now()
        s1 = Tournament.objects.create(
            name="Solo 1",
            game=self.game,
            organizer=self.user,
            description="Solo 1",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.SOLO,
            team_size=1,
            max_participants=4,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=5),
            contact_email="s1@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )
        s2 = Tournament.objects.create(
            name="Solo 2",
            game=self.game,
            organizer=self.user,
            description="Solo 2",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.SOLO,
            team_size=1,
            max_participants=4,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=5),
            contact_email="s2@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )

        register_solo_player(tournament=s1, user=player1)
        register_solo_player(tournament=s2, user=player1)

        self.client.login(username="multi_solo_p1", password="Password123!")
        response = self.client.get(reverse("dashboard:home"))
        context = response.context

        # Both tournaments appear in Joined Tournaments
        self.assertEqual(context["joined_tournaments_count"], 2)
        # No internal teams appear in My Teams
        self.assertEqual(len(context["user_teams"]), 0)

    def test_internal_solo_team_does_not_affect_my_teams_count(self):
        # TEST 5: My Teams count before = 1, after SOLO registration = 1 (NOT 2).
        player1 = User.objects.create_user(username="count_p1", password="Password123!")
        real_team = Team.objects.create(name="Real Count Team", manager=player1)
        TeamMember.objects.create(team=real_team, user=player1, team_role=TeamMember.TeamRole.MANAGER, is_active=True)

        self.client.login(username="count_p1", password="Password123!")
        res_before = self.client.get(reverse("dashboard:home"))
        self.assertEqual(len(res_before.context["user_teams"]), 1)

        # Register for SOLO tournament
        now = timezone.now()
        solo_t = Tournament.objects.create(
            name="Solo Count Tourney",
            game=self.game,
            organizer=self.user,
            description="Solo",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.SOLO,
            team_size=1,
            max_participants=4,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=5),
            contact_email="sc@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )
        register_solo_player(tournament=solo_t, user=player1)

        res_after = self.client.get(reverse("dashboard:home"))
        self.assertEqual(len(res_after.context["user_teams"]), 1)
        self.assertEqual(res_after.context["user_teams"][0], real_team)

    def test_team_list_view_excludes_internal_solo_teams(self):
        # TEST 6 & 8: TeamListView excludes internal solo teams.
        player1 = User.objects.create_user(username="team_list_p1", password="Password123!")
        real_team = Team.objects.create(name="Public Team", manager=player1)
        TeamMember.objects.create(team=real_team, user=player1, team_role=TeamMember.TeamRole.MANAGER, is_active=True)

        now = timezone.now()
        solo_t = Tournament.objects.create(
            name="Solo List Tourney",
            game=self.game,
            organizer=self.user,
            description="Solo",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.SOLO,
            team_size=1,
            max_participants=4,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=5),
            contact_email="sl@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )
        register_solo_player(tournament=solo_t, user=player1)

        self.client.login(username="team_list_p1", password="Password123!")
        response = self.client.get(reverse("teams:list"))
        self.assertEqual(response.status_code, 200)
        teams = response.context["teams"]
        self.assertEqual(len(teams), 1)
        self.assertEqual(teams[0], real_team)
