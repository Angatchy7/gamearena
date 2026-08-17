from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.teams.models import Team, TeamMember
from apps.teams.services import create_team, remove_team_member
from apps.tournaments.models import Game, Tournament, TournamentRegistration
from apps.tournaments.services import register_team
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class MultiTeamAndGameTests(TestCase):

    def setUp(self):
        self.mgr = User.objects.create_user(username="mgr_user", email="mgr@example.com", password="Password123!")
        self.player1 = User.objects.create_user(username="player1", email="p1@example.com", password="Password123!")
        self.player2 = User.objects.create_user(username="player2", email="p2@example.com", password="Password123!")

        self.game_pubg = Game.objects.create(name="PUBG Mobile", slug="pubg-mobile")
        self.game_val = Game.objects.create(name="Valorant", slug="valorant")

        self.client = APIClient()

    def test_user_can_manage_multiple_teams_different_games(self):
        res1 = create_team(manager=self.mgr, name="PUBG Squad", game=self.game_pubg)
        self.assertTrue(res1["success"])
        team_pubg = res1["team"]

        res2 = create_team(manager=self.mgr, name="Val Squad", game=self.game_val)
        self.assertTrue(res2["success"])
        team_val = res2["team"]

        self.assertEqual(Team.objects.filter(manager=self.mgr).count(), 2)
        self.assertEqual(team_pubg.game, self.game_pubg)
        self.assertEqual(team_val.game, self.game_val)

    def test_manager_cannot_create_two_teams_for_same_game(self):
        res1 = create_team(manager=self.mgr, name="PUBG Squad 1", game=self.game_pubg)
        self.assertTrue(res1["success"])

        res2 = create_team(manager=self.mgr, name="PUBG Squad 2", game=self.game_pubg)
        self.assertFalse(res2["success"])
        self.assertIn("already manage a team", res2["message"])

    def test_my_teams_api_and_game_filter(self):
        create_team(manager=self.mgr, name="PUBG Squad", game=self.game_pubg)
        create_team(manager=self.mgr, name="Val Squad", game=self.game_val)

        self.client.force_authenticate(user=self.mgr)

        res = self.client.get("/api/my-teams/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

        res_pubg = self.client.get("/api/my-teams/?game=pubg-mobile")
        self.assertEqual(res_pubg.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_pubg.data), 1)
        self.assertEqual(res_pubg.data[0]["name"], "PUBG Squad")

    def test_joined_teams_excludes_managed_teams(self):
        team_res = create_team(manager=self.mgr, name="PUBG Squad", game=self.game_pubg)
        team = team_res["team"]

        joined_qs = Team.objects.filter(
            members__user=self.mgr,
            members__is_active=True,
            is_active=True,
        ).exclude(manager=self.mgr).exclude(description="__SOLO_INTERNAL__")

        self.assertEqual(joined_qs.count(), 0)

    def test_soft_remove_member_preserves_history(self):
        team_res = create_team(manager=self.mgr, name="PUBG Squad", game=self.game_pubg)
        team = team_res["team"]

        membership = TeamMember.objects.create(team=team, user=self.player1, team_role=TeamMember.TeamRole.PLAYER)

        remove_res = remove_team_member(team=team, manager=self.mgr, member_user=self.player1)
        self.assertTrue(remove_res["success"])

        membership.refresh_from_db()
        self.assertFalse(membership.is_active)
        self.assertIsNotNone(membership.left_at)

        self.assertTrue(TeamMember.objects.filter(pk=membership.pk).exists())

    def test_registration_game_matching_and_duplicate_prevention(self):
        now = timezone.now()
        tourney_pubg = Tournament.objects.create(
            name="PUBG Open",
            slug="pubg-open",
            game=self.game_pubg,
            organizer=self.mgr,
            description="Desc",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.TEAM,
            team_size=1,
            max_participants=8,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=3),
            status=Tournament.Status.REGISTRATION_OPEN,
        )

        tourney_val = Tournament.objects.create(
            name="Val Open",
            slug="val-open",
            game=self.game_val,
            organizer=self.mgr,
            description="Desc",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.TEAM,
            team_size=1,
            max_participants=8,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=3),
            status=Tournament.Status.REGISTRATION_OPEN,
        )

        team_pubg = create_team(manager=self.mgr, name="PUBG Team", game=self.game_pubg)["team"]

        mismatch_res = register_team(tournament=tourney_val, team=team_pubg, user=self.mgr)
        self.assertFalse(mismatch_res["success"])
        self.assertIn("does not match", mismatch_res["message"])

        match_res = register_team(tournament=tourney_pubg, team=team_pubg, user=self.mgr)
        self.assertTrue(match_res["success"])

        dup_res = register_team(tournament=tourney_pubg, team=team_pubg, user=self.mgr)
        self.assertFalse(dup_res["success"])
        self.assertIn("already registered", dup_res["message"])

    def test_manager_can_delete_team_safely(self):
        from apps.teams.services import delete_team
        team_pubg = create_team(manager=self.mgr, name="PUBG Deletable", game=self.game_pubg)["team"]
        membership = TeamMember.objects.get(team=team_pubg, user=self.mgr)

        res = delete_team(team=team_pubg, user=self.mgr)
        self.assertTrue(res["success"])

        team_pubg.refresh_from_db()
        membership.refresh_from_db()

        self.assertFalse(team_pubg.is_active)
        self.assertFalse(membership.is_active)
        self.assertIsNotNone(membership.left_at)

    def test_non_manager_cannot_delete_team(self):
        from apps.teams.services import delete_team
        team_pubg = create_team(manager=self.mgr, name="PUBG Safe", game=self.game_pubg)["team"]

        res = delete_team(team=team_pubg, user=self.player1)
        self.assertFalse(res["success"])

        team_pubg.refresh_from_db()
        self.assertTrue(team_pubg.is_active)

    def test_deleted_team_cannot_register_for_tournament(self):
        from apps.teams.services import delete_team
        now = timezone.now()
        tourney_pubg = Tournament.objects.create(
            name="PUBG Open 2",
            slug="pubg-open-2",
            game=self.game_pubg,
            organizer=self.mgr,
            description="Desc",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.TEAM,
            team_size=1,
            max_participants=8,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=3),
            status=Tournament.Status.REGISTRATION_OPEN,
        )

        team_pubg = create_team(manager=self.mgr, name="PUBG Deactivated", game=self.game_pubg)["team"]
        delete_team(team=team_pubg, user=self.mgr)

        reg_res = register_team(tournament=tourney_pubg, team=team_pubg, user=self.mgr)
        self.assertFalse(reg_res["success"])
        self.assertIn("inactive", reg_res["message"].lower())

