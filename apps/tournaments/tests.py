import math
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from apps.teams.models import Team, TeamMember
from apps.tournaments.forms import TournamentCreateForm, TournamentRegistrationForm, MatchResultForm
from apps.tournaments.models import Game, Tournament, TournamentRegistration, Round, Match
from apps.tournaments.services import (
    create_tournament,
    update_tournament,
    publish_tournament,
    close_registration,
    cancel_tournament,
    register_team,
    register_solo_player,
    generate_single_elimination_bracket,
    advance_winner,
    get_tournament_statistics,
)

User = get_user_model()


def create_test_game(name="Valorant"):
    game, _ = Game.objects.get_or_create(
        name=name,
        defaults={"description": "FPS Game"}
    )
    return game



def create_test_tournament(organizer, game=None, max_participants=4, team_size=5, status=Tournament.Status.REGISTRATION_OPEN):
    if not game:
        game = create_test_game()
    now = timezone.now()
    return Tournament.objects.create(
        name="Champions Cup",
        game=game,
        organizer=organizer,
        description="Official Tournament",
        rules="Standard Rules",
        tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
        participation_type=Tournament.ParticipationType.TEAM,
        team_size=team_size,
        max_participants=max_participants,
        registration_start=now - timedelta(days=1),
        registration_end=now + timedelta(days=1),
        start_date=now + timedelta(days=2),
        end_date=now + timedelta(days=5),
        contact_email="organizer@example.com",
        status=status,
    )


def create_test_team(name, manager, member_count=5):
    team = Team.objects.create(name=name, manager=manager)
    # Add manager as MANAGER role
    TeamMember.objects.create(team=team, user=manager, team_role=TeamMember.TeamRole.MANAGER, is_active=True)
    # Add additional active members
    for i in range(1, member_count):
        u = User.objects.create_user(username=f"{name}_player_{i}", password="Password123!")
        TeamMember.objects.create(team=team, user=u, team_role=TeamMember.TeamRole.PLAYER, is_active=True)
    return team


class TournamentFormValidationTests(TestCase):
    """
    Tests form level date validation for tournament creation/editing.
    """

    def setUp(self):
        self.organizer = User.objects.create_user(username="org_form", password="Password123!")
        self.game = create_test_game("Dota 2")

    def test_form_valid_dates(self):
        now = timezone.now()
        form_data = {
            "name": "Dota Championship",
            "game": self.game.id,
            "description": "Desc",
            "rules": "Rules",
            "tournament_type": Tournament.TournamentType.SINGLE_ELIMINATION,
            "participation_type": Tournament.ParticipationType.TEAM,
            "team_size": 5,
            "max_participants": 8,
            "registration_fee": 0,
            "prize_pool": 1000,
            "registration_start": (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
            "registration_end": (now + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M"),
            "start_date": (now + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M"),
            "end_date": (now + timedelta(days=4)).strftime("%Y-%m-%dT%H:%M"),
            "contact_email": "org@example.com",
            "visibility": Tournament.Visibility.PUBLIC,
        }
        form = TournamentCreateForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_invalid_registration_end_before_start(self):
        now = timezone.now()
        form_data = {
            "name": "Invalid Reg Dates",
            "game": self.game.id,
            "description": "Desc",
            "rules": "Rules",
            "tournament_type": Tournament.TournamentType.SINGLE_ELIMINATION,
            "participation_type": Tournament.ParticipationType.TEAM,
            "team_size": 5,
            "max_participants": 8,
            "registration_start": (now + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M"),
            "registration_end": (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
            "start_date": (now + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M"),
            "end_date": (now + timedelta(days=4)).strftime("%Y-%m-%dT%H:%M"),
            "contact_email": "org@example.com",
            "visibility": Tournament.Visibility.PUBLIC,
        }
        form = TournamentCreateForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("registration_end", form.errors)


class TournamentRegistrationBusinessRuleTests(TestCase):
    """
    Tests team registration requirements, capacity N-1, N, N+1 boundaries, duplicate protection.
    """

    def setUp(self):
        self.organizer = User.objects.create_user(username="tourney_org", password="Password123!")
        self.tournament = create_test_tournament(organizer=self.organizer, max_participants=2, team_size=5)

        self.mgr1 = User.objects.create_user(username="tm_mgr1", password="Password123!")
        self.team1 = create_test_team("Team Alpha", self.mgr1, member_count=5)

        self.mgr2 = User.objects.create_user(username="tm_mgr2", password="Password123!")
        self.team2 = create_test_team("Team Beta", self.mgr2, member_count=5)

        self.mgr3 = User.objects.create_user(username="tm_mgr3", password="Password123!")
        self.team3 = create_test_team("Team Gamma", self.mgr3, member_count=5)

    def test_valid_team_registration(self):
        res = register_team(tournament=self.tournament, team=self.team1, user=self.mgr1)
        self.assertTrue(res["success"])
        self.assertTrue(TournamentRegistration.objects.filter(tournament=self.tournament, team=self.team1).exists())

    def test_duplicate_registration_rejected(self):
        register_team(tournament=self.tournament, team=self.team1, user=self.mgr1)
        res2 = register_team(tournament=self.tournament, team=self.team1, user=self.mgr1)
        self.assertFalse(res2["success"])
        self.assertEqual(res2["message"], "Team is already registered.")

    def test_duplicate_registration_db_constraint(self):
        register_team(tournament=self.tournament, team=self.team1, user=self.mgr1)
        with self.assertRaises(IntegrityError):
            TournamentRegistration.objects.create(tournament=self.tournament, team=self.team1, registered_by=self.mgr1)

    def test_capacity_boundary_n_minus_1_n_n_plus_1(self):
        # Tournament max_participants = 2
        # Registration 1 (N-1 = 1 team registered out of 2 max) -> Success
        res1 = register_team(tournament=self.tournament, team=self.team1, user=self.mgr1)
        self.assertTrue(res1["success"])
        self.assertEqual(TournamentRegistration.objects.filter(tournament=self.tournament).count(), 1)

        # Registration 2 (N = 2 teams registered out of 2 max) -> Success (Tournament Full)
        res2 = register_team(tournament=self.tournament, team=self.team2, user=self.mgr2)
        self.assertTrue(res2["success"])
        self.assertEqual(TournamentRegistration.objects.filter(tournament=self.tournament).count(), 2)

        # Registration 3 (N+1 attempt) -> Rejection!
        res3 = register_team(tournament=self.tournament, team=self.team3, user=self.mgr3)
        self.assertFalse(res3["success"])
        self.assertEqual(res3["message"], "Tournament is already full.")
        self.assertEqual(TournamentRegistration.objects.filter(tournament=self.tournament).count(), 2)

    def test_registration_with_insufficient_active_players_rejected(self):
        small_mgr = User.objects.create_user(username="small_mgr", password="Password123!")
        small_team = create_test_team("Understaffed", small_mgr, member_count=3)  # Only 3 active players, requires 5
        res = register_team(tournament=self.tournament, team=small_team, user=small_mgr)
        self.assertFalse(res["success"])
        self.assertIn("requires 5 players", res["message"])

    def test_registration_with_inactive_team_rejected(self):
        inact_mgr = User.objects.create_user(username="inact_mgr", password="Password123!")
        inact_team = create_test_team("Inactive Team", inact_mgr, member_count=5)
        inact_team.is_active = False
        inact_team.save()

        res = register_team(tournament=self.tournament, team=inact_team, user=inact_mgr)
        self.assertFalse(res["success"])
        self.assertEqual(res["message"], "This team is inactive.")

    def test_registration_by_non_manager_rejected(self):
        other_user = User.objects.create_user(username="imposter", password="Password123!")
        res = register_team(tournament=self.tournament, team=self.team1, user=other_user)
        self.assertFalse(res["success"])
        self.assertEqual(res["message"], "Only the team manager can register the team.")

    def test_registration_closed_status_rejected(self):
        self.tournament.status = Tournament.Status.REGISTRATION_CLOSED
        self.tournament.save()
        res = register_team(tournament=self.tournament, team=self.team1, user=self.mgr1)
        self.assertFalse(res["success"])
        self.assertEqual(res["message"], "Tournament registration is closed.")


class TournamentLifecycleTests(TestCase):
    """
    Tests state transitions for Tournament status.
    """

    def setUp(self):
        self.organizer = User.objects.create_user(username="lifecycle_org", password="Password123!")
        self.tournament = create_test_tournament(organizer=self.organizer, status=Tournament.Status.DRAFT)

    def test_publish_tournament(self):
        publish_tournament(tournament=self.tournament)
        self.tournament.refresh_from_db()
        self.assertEqual(self.tournament.status, Tournament.Status.REGISTRATION_OPEN)

    def test_close_registration(self):
        close_registration(tournament=self.tournament)
        self.tournament.refresh_from_db()
        self.assertEqual(self.tournament.status, Tournament.Status.REGISTRATION_CLOSED)

    def test_cancel_tournament(self):
        cancel_tournament(tournament=self.tournament)
        self.tournament.refresh_from_db()
        self.assertEqual(self.tournament.status, Tournament.Status.CANCELLED)


class BracketGenerationTests(TestCase):
    """
    Tests bracket generation for 2, 4, 8, 16 teams, non-power-of-two team counts, BYE handling, and structural invariants.
    """

    def setUp(self):
        self.organizer = User.objects.create_user(username="bracket_org", password="Password123!")

    def _setup_tournament_with_teams(self, count):
        tournament = create_test_tournament(organizer=self.organizer, max_participants=count)
        teams = []
        for i in range(count):
            mgr = User.objects.create_user(username=f"b_mgr_{count}_{i}", password="Password123!")
            team = create_test_team(f"Team_{count}_{i}", mgr, member_count=5)
            register_team(tournament=tournament, team=team, user=mgr)
            teams.append(team)
        return tournament, teams

    def test_bracket_generation_2_teams(self):
        t, teams = self._setup_tournament_with_teams(2)
        res = generate_single_elimination_bracket(tournament=t)
        self.assertTrue(res["success"])

        rounds = Round.objects.filter(tournament=t).order_by("order")
        self.assertEqual(rounds.count(), 1)  # log2(2) = 1 round
        matches = Match.objects.filter(round=rounds[0])
        self.assertEqual(matches.count(), 1)

        m = matches.first()
        self.assertIn(m.team_one, teams)
        self.assertIn(m.team_two, teams)
        self.assertNotEqual(m.team_one, m.team_two)

    def test_bracket_generation_4_teams(self):
        t, teams = self._setup_tournament_with_teams(4)
        res = generate_single_elimination_bracket(tournament=t)
        self.assertTrue(res["success"])

        rounds = list(Round.objects.filter(tournament=t).order_by("order"))
        self.assertEqual(len(rounds), 2)  # log2(4) = 2 rounds

        r1_matches = list(Match.objects.filter(round=rounds[0]).order_by("match_number"))
        self.assertEqual(len(r1_matches), 2)
        r2_matches = list(Match.objects.filter(round=rounds[1]).order_by("match_number"))
        self.assertEqual(len(r2_matches), 1)

    def test_bracket_generation_8_teams(self):
        t, teams = self._setup_tournament_with_teams(8)
        res = generate_single_elimination_bracket(tournament=t)
        self.assertTrue(res["success"])

        rounds = list(Round.objects.filter(tournament=t).order_by("order"))
        self.assertEqual(len(rounds), 3)  # log2(8) = 3 rounds
        self.assertEqual(Match.objects.filter(round__tournament=t).count(), 7)

    def test_bracket_generation_16_teams(self):
        t, teams = self._setup_tournament_with_teams(16)
        res = generate_single_elimination_bracket(tournament=t)
        self.assertTrue(res["success"])

        rounds = list(Round.objects.filter(tournament=t).order_by("order"))
        self.assertEqual(len(rounds), 4)  # log2(16) = 4 rounds
        self.assertEqual(Match.objects.filter(round__tournament=t).count(), 15)

    def test_bracket_generation_3_teams_with_bye(self):
        t, teams = self._setup_tournament_with_teams(3)
        res = generate_single_elimination_bracket(tournament=t)
        self.assertTrue(res["success"])

        rounds = list(Round.objects.filter(tournament=t).order_by("order"))
        self.assertEqual(len(rounds), 2)  # 3 teams -> bracket size 4 -> 2 rounds

        r1_matches = Match.objects.filter(round=rounds[0]).order_by("match_number")
        # One match in round 1 should have a BYE and be automatically completed
        bye_matches = [m for m in r1_matches if m.status == Match.Status.COMPLETED]
        self.assertEqual(len(bye_matches), 1)
        bye_match = bye_matches[0]
        self.assertIsNotNone(bye_match.winner)

        # Check winner advanced to round 2 match
        r2_match = Match.objects.filter(round=rounds[1]).first()
        self.assertTrue(r2_match.team_one == bye_match.winner or r2_match.team_two == bye_match.winner)

    def test_prevent_duplicate_bracket_generation(self):
        t, teams = self._setup_tournament_with_teams(4)
        res1 = generate_single_elimination_bracket(tournament=t)
        self.assertTrue(res1["success"])

        res2 = generate_single_elimination_bracket(tournament=t)
        self.assertFalse(res2["success"])
        self.assertEqual(res2["message"], "Bracket already exists.")

    def test_bracket_generation_insufficient_teams(self):
        t, teams = self._setup_tournament_with_teams(1)
        res = generate_single_elimination_bracket(tournament=t)
        self.assertFalse(res["success"])
        self.assertEqual(res["message"], "At least two teams are required.")


class MatchProgressionAndChampionTests(TestCase):
    """
    Tests match score updates, tie rejection, winner progression through rounds, and champion declaration.
    """

    def setUp(self):
        self.client = Client()
        self.organizer = User.objects.create_user(username="prog_org", password="Password123!")
        self.tournament = create_test_tournament(organizer=self.organizer, max_participants=4)
        self.teams = []
        for i in range(4):
            mgr = User.objects.create_user(username=f"p_mgr_{i}", password="Password123!")
            team = create_test_team(f"ProgTeam_{i}", mgr)
            register_team(tournament=self.tournament, team=team, user=mgr)
            self.teams.append(team)

        generate_single_elimination_bracket(tournament=self.tournament)
        self.rounds = list(Round.objects.filter(tournament=self.tournament).order_by("order"))

    def test_score_submission_and_winner_advancement(self):
        # Round 1, Match 1
        r1_m1 = Match.objects.filter(round=self.rounds[0], match_number=1).first()
        r1_m1.team_one_score = 2
        r1_m1.team_two_score = 1
        r1_m1.winner = r1_m1.team_one
        r1_m1.status = Match.Status.COMPLETED
        r1_m1.save()

        advance_winner(match=r1_m1)

        # Check Round 2 Match 1 received winner of R1M1 in team_one position (since match_number 1 is odd)
        r2_m1 = Match.objects.filter(round=self.rounds[1], match_number=1).first()
        self.assertEqual(r2_m1.team_one, r1_m1.winner)

    def test_tie_score_rejection_in_match_detail_view(self):
        self.client.login(username="prog_org", password="Password123!")
        r1_m1 = Match.objects.filter(round=self.rounds[0], match_number=1).first()

        url = reverse("tournaments:match_detail", kwargs={"pk": r1_m1.pk})
        post_data = {"team_one_score": 1, "team_two_score": 1}
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tie scores are not allowed")

        r1_m1.refresh_from_db()
        self.assertEqual(r1_m1.status, Match.Status.PENDING)

    def test_tournament_champion_assignment_on_final_completion(self):
        # Round 1 Match 1
        m1 = Match.objects.filter(round=self.rounds[0], match_number=1).first()
        m1.team_one_score = 3
        m1.team_two_score = 0
        m1.winner = m1.team_one
        m1.status = Match.Status.COMPLETED
        m1.save()
        advance_winner(match=m1)

        # Round 1 Match 2
        m2 = Match.objects.filter(round=self.rounds[0], match_number=2).first()
        m2.team_one_score = 2
        m2.team_two_score = 1
        m2.winner = m2.team_one
        m2.status = Match.Status.COMPLETED
        m2.save()
        advance_winner(match=m2)

        # Final Match (Round 2 Match 1)
        final_match = Match.objects.filter(round=self.rounds[1], match_number=1).first()
        self.assertIsNotNone(final_match.team_one)
        self.assertIsNotNone(final_match.team_two)

        final_match.team_one_score = 5
        final_match.team_two_score = 2
        final_match.winner = final_match.team_one
        final_match.status = Match.Status.COMPLETED
        final_match.save()

        advance_winner(match=final_match)

        self.tournament.refresh_from_db()
        self.assertEqual(self.tournament.champion, final_match.winner)
        self.assertEqual(self.tournament.status, Tournament.Status.COMPLETED)

    def test_unauthorized_user_cannot_update_match(self):
        attacker = User.objects.create_user(username="match_hacker", password="Password123!")
        self.client.login(username="match_hacker", password="Password123!")
        r1_m1 = Match.objects.filter(round=self.rounds[0], match_number=1).first()

        url = reverse("tournaments:match_detail", kwargs={"pk": r1_m1.pk})
        post_data = {"team_one_score": 10, "team_two_score": 0}
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 403)


class LeaderboardAndStatisticsDataTests(TestCase):
    """
    Tests get_tournament_statistics calculation for wins, losses, points, win_rate, and leaderboard ranking.
    """

    def setUp(self):
        self.organizer = User.objects.create_user(username="stats_org", password="Password123!")
        self.tournament = create_test_tournament(organizer=self.organizer, max_participants=2)

        self.mgr1 = User.objects.create_user(username="s_mgr1", password="Password123!")
        self.team_a = create_test_team("Team Alpha", self.mgr1)
        register_team(tournament=self.tournament, team=self.team_a, user=self.mgr1)

        self.mgr2 = User.objects.create_user(username="s_mgr2", password="Password123!")
        self.team_b = create_test_team("Team Beta", self.mgr2)
        register_team(tournament=self.tournament, team=self.team_b, user=self.mgr2)

        generate_single_elimination_bracket(tournament=self.tournament)
        self.r1 = Round.objects.filter(tournament=self.tournament).first()
        self.match = Match.objects.filter(round=self.r1).first()

    def test_leaderboard_statistics_calculation(self):
        self.match.team_one = self.team_a
        self.match.team_two = self.team_b
        self.match.team_one_score = 4
        self.match.team_two_score = 1
        self.match.winner = self.team_a
        self.match.status = Match.Status.COMPLETED
        self.match.save()

        stats = get_tournament_statistics(tournament=self.tournament)

        self.assertEqual(stats["total_matches_count"], 1)
        self.assertEqual(stats["completed_matches_count"], 1)
        self.assertEqual(stats["completion_percentage"], 100)
        self.assertEqual(stats["total_goals"], 5)
        self.assertEqual(stats["avg_goals"], 5.0)

        rankings = stats["team_rankings"]
        self.assertEqual(len(rankings), 2)

        top_team = rankings[0]
        self.assertEqual(top_team["team"], self.team_a)
        self.assertEqual(top_team["wins"], 1)
        self.assertEqual(top_team["losses"], 0)
        self.assertEqual(top_team["points"], 3)
        self.assertEqual(top_team["goals_scored"], 4)
        self.assertEqual(top_team["goals_conceded"], 1)
        self.assertEqual(top_team["goal_difference"], 3)

        second_team = rankings[1]
        self.assertEqual(second_team["team"], self.team_b)
        self.assertEqual(second_team["wins"], 0)
        self.assertEqual(second_team["losses"], 1)
        self.assertEqual(second_team["points"], 0)


class SearchAndFilterTests(TestCase):
    """
    Tests tournament search by query, game slug filter, and combined filtering.
    """

    def setUp(self):
        self.client = Client()
        self.organizer = User.objects.create_user(username="search_org", password="Password123!")

        self.game_pubg = Game.objects.create(name="PUBG Mobile", slug="pubg-mobile")
        self.game_cs = Game.objects.create(name="CS:GO", slug="csgo")

        self.t1 = create_test_tournament(organizer=self.organizer, game=self.game_pubg)
        self.t1.name = "PUBG Global Championship"
        self.t1.description = "Battle Royale Tournament"
        self.t1.save()

        self.t2 = create_test_tournament(organizer=self.organizer, game=self.game_cs)
        self.t2.name = "CS Major Masters"
        self.t2.description = "Tactical Shooter Event"
        self.t2.save()

    def test_search_by_query_exact_and_partial(self):
        url = reverse("tournaments:list")
        response = self.client.get(url, {"q": "PUBG"})
        self.assertEqual(response.status_code, 200)
        tournaments = list(response.context["tournaments"])
        self.assertEqual(len(tournaments), 1)
        self.assertEqual(tournaments[0], self.t1)

    def test_search_by_game_filter(self):
        url = reverse("tournaments:list")
        response = self.client.get(url, {"game": "csgo"})
        self.assertEqual(response.status_code, 200)
        tournaments = list(response.context["tournaments"])
        self.assertEqual(len(tournaments), 1)
        self.assertEqual(tournaments[0], self.t2)

    def test_search_combined_query_and_game_filter(self):
        url = reverse("tournaments:list")
        response = self.client.get(url, {"q": "PUBG", "game": "pubg-mobile"})
        self.assertEqual(response.status_code, 200)
        tournaments = list(response.context["tournaments"])
        self.assertEqual(len(tournaments), 1)
        self.assertEqual(tournaments[0], self.t1)

    def test_search_no_results(self):
        url = reverse("tournaments:list")
        response = self.client.get(url, {"q": "NonExistentGame"})
        self.assertEqual(response.status_code, 200)
        tournaments = list(response.context["tournaments"])
        self.assertEqual(len(tournaments), 0)


class NonPowerOfTwoBracketRegressionTests(TestCase):
    """
    Regression tests verifying bracket generation, BYE interleaving, winner progression,
    and full tournament completion for non-power-of-two team counts (3, 5, 6, 7, 9, 10, 12, 15).
    """

    def setUp(self):
        self.organizer = User.objects.create_user(username="reg_org", password="Password123!")

    def _setup_and_verify_bracket(self, count):
        tournament = create_test_tournament(organizer=self.organizer, max_participants=count)
        teams = []
        for i in range(count):
            mgr = User.objects.create_user(username=f"reg_mgr_{count}_{i}", password="Password123!")
            team = create_test_team(f"RegTeam_{count}_{i}", mgr)
            register_team(tournament=tournament, team=team, user=mgr)
            teams.append(team)

        res = generate_single_elimination_bracket(tournament=tournament)
        self.assertTrue(res["success"])

        # Compute expected numbers
        bracket_size = 1
        while bracket_size < count:
            bracket_size *= 2

        expected_byes = bracket_size - count
        expected_r1_matches = bracket_size // 2

        rounds = list(Round.objects.filter(tournament=tournament).order_by("order"))
        self.assertEqual(len(rounds), int(math.log2(bracket_size)))

        r1_matches = list(Match.objects.filter(round=rounds[0]).order_by("match_number"))
        self.assertEqual(len(r1_matches), expected_r1_matches)

        # Assert NO Round 1 match has both team_one and team_two as None
        for m in r1_matches:
            self.assertFalse(
                m.team_one is None and m.team_two is None,
                f"Round 1 Match {m.id} has both teams as None for {count} teams"
            )

        # Check Round 1 team occurrences
        real_teams_in_r1 = []
        byes_in_r1 = 0
        for m in r1_matches:
            if m.team_one:
                real_teams_in_r1.append(m.team_one)
            else:
                byes_in_r1 += 1

            if m.team_two:
                real_teams_in_r1.append(m.team_two)
            else:
                byes_in_r1 += 1

        self.assertEqual(len(real_teams_in_r1), count)
        self.assertEqual(len(set(real_teams_in_r1)), count)  # Every team appears exactly once
        self.assertEqual(byes_in_r1, expected_byes)

        # Simulate playing out all rounds from Round 1 to Final
        for r in rounds:
            r_matches = list(Match.objects.filter(round=r).order_by("match_number"))
            for m in r_matches:
                m.refresh_from_db()
                if r.order == 1 and (m.team_one is None or m.team_two is None):
                    # In Round 1, BYE matches have 1 team and 1 None
                    self.assertTrue(
                        (m.team_one is not None and m.team_two is None) or (m.team_one is None and m.team_two is not None),
                        f"Match {m.id} in Round 1 has invalid BYE pairing for {count} teams"
                    )
                else:
                    self.assertIsNotNone(m.team_one, f"Match {m.id} in {r.name} missing team_one for {count} teams")
                    self.assertIsNotNone(m.team_two, f"Match {m.id} in {r.name} missing team_two for {count} teams")

                if m.status != Match.Status.COMPLETED:
                    m.team_one_score = 2
                    m.team_two_score = 1
                    m.winner = m.team_one
                    m.status = Match.Status.COMPLETED
                    m.save()
                    advance_winner(match=m)

        tournament.refresh_from_db()
        self.assertIsNotNone(tournament.champion, f"Champion not assigned for {count} teams")
        self.assertEqual(tournament.status, Tournament.Status.COMPLETED, f"Tournament not completed for {count} teams")

    def test_bracket_3_teams(self):
        self._setup_and_verify_bracket(3)

    def test_bracket_5_teams(self):
        self._setup_and_verify_bracket(5)

    def test_bracket_6_teams(self):
        self._setup_and_verify_bracket(6)

    def test_bracket_7_teams(self):
        self._setup_and_verify_bracket(7)

    def test_bracket_9_teams(self):
        self._setup_and_verify_bracket(9)

    def test_bracket_10_teams(self):
        self._setup_and_verify_bracket(10)

    def test_bracket_12_teams(self):
        self._setup_and_verify_bracket(12)

    def test_bracket_15_teams(self):
        self._setup_and_verify_bracket(15)


class TournamentPlayerUniquenessTests(TestCase):
    """
    Tests for Requirement 1: Player uniqueness within the same tournament.
    """

    def setUp(self):
        self.organizer = User.objects.create_user(username="org_uniq", password="Password123!")
        self.tournament1 = create_test_tournament(organizer=self.organizer, max_participants=4, team_size=2)
        self.tournament2 = create_test_tournament(organizer=self.organizer, max_participants=4, team_size=2)

        # Shared player
        self.player1 = User.objects.create_user(username="shared_p1", password="Password123!")
        self.player2 = User.objects.create_user(username="p2", password="Password123!")
        self.player3 = User.objects.create_user(username="p3", password="Password123!")

        # Team A: player1 & player2
        self.mgr_a = User.objects.create_user(username="mgr_a", password="Password123!")
        self.team_a = Team.objects.create(name="Team A", manager=self.mgr_a)
        TeamMember.objects.create(team=self.team_a, user=self.mgr_a, team_role=TeamMember.TeamRole.MANAGER, is_active=True)
        TeamMember.objects.create(team=self.team_a, user=self.player1, team_role=TeamMember.TeamRole.PLAYER, is_active=True)
        TeamMember.objects.create(team=self.team_a, user=self.player2, team_role=TeamMember.TeamRole.PLAYER, is_active=True)

        # Team B: player1 & player3 (overlaps with Team A on player1)
        self.mgr_b = User.objects.create_user(username="mgr_b", password="Password123!")
        self.team_b = Team.objects.create(name="Team B", manager=self.mgr_b)
        TeamMember.objects.create(team=self.team_b, user=self.mgr_b, team_role=TeamMember.TeamRole.MANAGER, is_active=True)
        TeamMember.objects.create(team=self.team_b, user=self.player1, team_role=TeamMember.TeamRole.PLAYER, is_active=True)
        TeamMember.objects.create(team=self.team_b, user=self.player3, team_role=TeamMember.TeamRole.PLAYER, is_active=True)

        # Team C: completely different players
        self.mgr_c = User.objects.create_user(username="mgr_c", password="Password123!")
        self.team_c = create_test_team("Team C", self.mgr_c, member_count=2)

    def test_player_in_team_a_cannot_register_team_b_in_same_tournament(self):
        res_a = register_team(tournament=self.tournament1, team=self.team_a, user=self.mgr_a)
        self.assertTrue(res_a["success"])

        res_b = register_team(tournament=self.tournament1, team=self.team_b, user=self.mgr_b)
        self.assertFalse(res_b["success"])
        self.assertEqual(
            res_b["message"],
            "One or more players are already registered with another team in this tournament."
        )

    def test_player_in_team_a_can_participate_in_another_tournament(self):
        res_a = register_team(tournament=self.tournament1, team=self.team_a, user=self.mgr_a)
        self.assertTrue(res_a["success"])

        # Same player in Team B registering for Tournament 2 MUST be allowed
        res_b = register_team(tournament=self.tournament2, team=self.team_b, user=self.mgr_b)
        self.assertTrue(res_b["success"])

    def test_multiple_overlapping_players_rejected(self):
        # Create Team D with both player1 and player2
        mgr_d = User.objects.create_user(username="mgr_d", password="Password123!")
        team_d = Team.objects.create(name="Team D", manager=mgr_d)
        TeamMember.objects.create(team=team_d, user=mgr_d, team_role=TeamMember.TeamRole.MANAGER, is_active=True)
        TeamMember.objects.create(team=team_d, user=self.player1, team_role=TeamMember.TeamRole.PLAYER, is_active=True)
        TeamMember.objects.create(team=team_d, user=self.player2, team_role=TeamMember.TeamRole.PLAYER, is_active=True)

        register_team(tournament=self.tournament1, team=self.team_a, user=self.mgr_a)
        res_d = register_team(tournament=self.tournament1, team=team_d, user=mgr_d)
        self.assertFalse(res_d["success"])

    def test_teams_with_different_players_can_register(self):
        res_a = register_team(tournament=self.tournament1, team=self.team_a, user=self.mgr_a)
        res_c = register_team(tournament=self.tournament1, team=self.team_c, user=self.mgr_c)
        self.assertTrue(res_a["success"])
        self.assertTrue(res_c["success"])

    def test_inactive_team_members_do_not_trigger_conflict(self):
        # Deactivate player1 in Team A
        mem = TeamMember.objects.get(team=self.team_a, user=self.player1)
        mem.is_active = False
        mem.save()

        # Add another active player to Team A so team_size=2 requirement is met
        extra_p = User.objects.create_user(username="extra_p", password="Password123!")
        TeamMember.objects.create(team=self.team_a, user=extra_p, team_role=TeamMember.TeamRole.PLAYER, is_active=True)

        register_team(tournament=self.tournament1, team=self.team_a, user=self.mgr_a)

        # Team B has player1 active -> Should NOT conflict because player1 was inactive in Team A
        res_b = register_team(tournament=self.tournament1, team=self.team_b, user=self.mgr_b)
        self.assertTrue(res_b["success"])


class SoloTournamentBusinessRuleTests(TestCase):
    """
    Tests for Requirements 2, 3, 4, 5, 8: SOLO tournament team_size=1, individual registration, capacity, and UI action strings.
    """

    def setUp(self):
        self.organizer = User.objects.create_user(username="solo_org", password="Password123!")
        self.game = create_test_game("FC 26")
        now = timezone.now()
        self.solo_tournament = Tournament.objects.create(
            name="FIFA Solo Championship",
            game=self.game,
            organizer=self.organizer,
            description="Solo Tournament",
            rules="Solo Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.SOLO,
            team_size=5,  # Submitted as 5, should force to 1
            max_participants=4,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=5),
            contact_email="solo@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )
        self.p1 = User.objects.create_user(username="solo_player1", password="Password123!")
        self.p2 = User.objects.create_user(username="solo_player2", password="Password123!")
        self.p3 = User.objects.create_user(username="solo_player3", password="Password123!")
        self.p4 = User.objects.create_user(username="solo_player4", password="Password123!")
        self.p5 = User.objects.create_user(username="solo_player5", password="Password123!")

        self.client = Client()

    def test_solo_tournament_forces_team_size_one(self):
        self.solo_tournament.refresh_from_db()
        self.assertEqual(self.solo_tournament.team_size, 1)

    def test_solo_tournament_form_validates_team_size(self):
        now = timezone.now()
        form_data = {
            "name": "Solo Cup",
            "game": self.game.id,
            "description": "Desc",
            "rules": "Rules",
            "tournament_type": Tournament.TournamentType.SINGLE_ELIMINATION,
            "participation_type": Tournament.ParticipationType.SOLO,
            "team_size": 5,
            "max_participants": 8,
            "registration_fee": 0,
            "prize_pool": 500,
            "registration_start": (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
            "registration_end": (now + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M"),
            "start_date": (now + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M"),
            "end_date": (now + timedelta(days=4)).strftime("%Y-%m-%dT%H:%M"),
            "contact_email": "solo@example.com",
            "visibility": Tournament.Visibility.PUBLIC,
        }
        form = TournamentCreateForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("team_size", form.errors)

    def test_solo_player_individual_registration(self):
        res = register_solo_player(tournament=self.solo_tournament, user=self.p1)
        self.assertTrue(res["success"])
        self.assertTrue(TournamentRegistration.objects.filter(tournament=self.solo_tournament, user=self.p1).exists())

    def test_solo_player_cannot_register_twice(self):
        res1 = register_solo_player(tournament=self.solo_tournament, user=self.p1)
        self.assertTrue(res1["success"])

        res2 = register_solo_player(tournament=self.solo_tournament, user=self.p1)
        self.assertFalse(res2["success"])
        self.assertEqual(res2["message"], "You are already registered for this tournament.")

    def test_solo_capacity_boundary_n_minus_1_n_n_plus_1(self):
        # Capacity max_participants = 4
        res1 = register_solo_player(tournament=self.solo_tournament, user=self.p1)
        res2 = register_solo_player(tournament=self.solo_tournament, user=self.p2)
        res3 = register_solo_player(tournament=self.solo_tournament, user=self.p3) # N-1 = 3 -> Success
        self.assertTrue(res3["success"])

        res4 = register_solo_player(tournament=self.solo_tournament, user=self.p4) # N = 4 -> Success (Full)
        self.assertTrue(res4["success"])

        res5 = register_solo_player(tournament=self.solo_tournament, user=self.p5) # N+1 -> Rejection
        self.assertFalse(res5["success"])
        self.assertEqual(res5["message"], "Tournament is already full.")

    def test_team_tournament_registration_preserved(self):
        mgr = User.objects.create_user(username="team_mgr_pres", password="Password123!")
        team = create_test_team("Team Preserved", mgr, member_count=5)
        team_tourney = create_test_tournament(organizer=self.organizer, max_participants=4, team_size=5)
        res = register_team(tournament=team_tourney, team=team, user=mgr)
        self.assertTrue(res["success"])

    def test_ui_display_action_labels_solo_vs_team(self):
        self.client.login(username="solo_player1", password="Password123!")

        # SOLO tournament registration page shows "Register"
        url_solo = reverse("tournaments:register", kwargs={"slug": self.solo_tournament.slug})
        resp_solo = self.client.get(url_solo)
        self.assertEqual(resp_solo.status_code, 200)
        self.assertContains(resp_solo, "Register for Tournament")
        self.assertNotContains(resp_solo, "Select Team")

        # TEAM tournament registration page shows "Register Team"
        team_tourney = create_test_tournament(organizer=self.organizer, max_participants=4, team_size=5)
        url_team = reverse("tournaments:register", kwargs={"slug": team_tourney.slug})
        resp_team = self.client.get(url_team)
        self.assertEqual(resp_team.status_code, 200)
        self.assertContains(resp_team, "Register Team")

    def test_unauthenticated_users_cannot_register(self):
        url = reverse("tournaments:register", kwargs={"slug": self.solo_tournament.slug})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_manager_cannot_register_player_already_in_same_tournament(self):
        # Create team T1 with p1, T2 with p1
        mgr1 = User.objects.create_user(username="m1_sec", password="Password123!")
        t1 = create_test_team("T1 Sec", mgr1, member_count=2)
        # Add p1 to t1
        TeamMember.objects.create(team=t1, user=self.p1, team_role=TeamMember.TeamRole.PLAYER, is_active=True)

        mgr2 = User.objects.create_user(username="m2_sec", password="Password123!")
        t2 = create_test_team("T2 Sec", mgr2, member_count=2)
        # Add p1 to t2 as well
        TeamMember.objects.create(team=t2, user=self.p1, team_role=TeamMember.TeamRole.PLAYER, is_active=True)

        team_tourney = create_test_tournament(organizer=self.organizer, max_participants=4, team_size=2)
        register_team(tournament=team_tourney, team=t1, user=mgr1)

        # mgr2 trying to register t2 should be rejected because p1 is already registered in t1
        res = register_team(tournament=team_tourney, team=t2, user=mgr2)
        self.assertFalse(res["success"])
        self.assertEqual(res["message"], "One or more players are already registered with another team in this tournament.")


class SoloTournamentBracketRegressionTests(TestCase):
    """
    Regression tests for bracket generation and match progression in SOLO tournaments for 2, 3, 5, 6, 7, and 8 participants.
    """

    def setUp(self):
        self.organizer = User.objects.create_user(username="solo_bracket_org", password="Password123!")
        self.game = create_test_game("FC 26 Solo")

    def _setup_and_verify_solo_bracket(self, count):
        now = timezone.now()
        tourney = Tournament.objects.create(
            name=f"Solo Tournament {count} Players",
            game=self.game,
            organizer=self.organizer,
            description="Bracket test",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.SOLO,
            team_size=1,
            max_participants=count,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=5),
            contact_email="solo@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )

        players = []
        for i in range(1, count + 1):
            p = User.objects.create_user(username=f"solo_{count}_player_{i}", password="Password123!")
            players.append(p)
            res = register_solo_player(tournament=tourney, user=p)
            self.assertTrue(res["success"], f"Failed to register solo player {i} for {count} players")

        tourney.status = Tournament.Status.REGISTRATION_CLOSED
        tourney.save()

        res_bracket = generate_single_elimination_bracket(tournament=tourney)
        self.assertTrue(res_bracket["success"], f"Failed to generate bracket for {count} solo players: {res_bracket.get('message')}")

        rounds = Round.objects.filter(tournament=tourney).order_by("order")
        self.assertGreater(rounds.count(), 0)

        # Play out all matches
        for r in rounds:
            matches = Match.objects.filter(round=r).order_by("match_number")
            for m in matches:
                if r.order == 1:
                    self.assertTrue(
                        m.team_one is not None or m.team_two is not None,
                        f"Match {m.id} in Round 1 for {count} solo players has no teams"
                    )

                if m.status != Match.Status.COMPLETED:
                    m.team_one_score = 2
                    m.team_two_score = 1
                    m.winner = m.team_one
                    m.status = Match.Status.COMPLETED
                    m.save()
                    advance_winner(match=m)

        tourney.refresh_from_db()
        self.assertIsNotNone(tourney.champion, f"Champion not assigned for {count} solo players")
        self.assertEqual(tourney.status, Tournament.Status.COMPLETED, f"Tournament not completed for {count} solo players")

    def test_solo_bracket_2_players(self):
        self._setup_and_verify_solo_bracket(2)

    def test_solo_bracket_3_players(self):
        self._setup_and_verify_solo_bracket(3)

    def test_solo_bracket_5_players(self):
        self._setup_and_verify_solo_bracket(5)

    def test_solo_bracket_6_players(self):
        self._setup_and_verify_solo_bracket(6)

    def test_solo_bracket_7_players(self):
        self._setup_and_verify_solo_bracket(7)

    def test_solo_bracket_8_players(self):
        self._setup_and_verify_solo_bracket(8)


class BusinessRuleValidationTests(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(username="rule_org", password="Password123!")
        self.player1 = User.objects.create_user(username="rule_player1", password="Password123!")
        self.player2 = User.objects.create_user(username="rule_player2", password="Password123!")

    def test_game_sharing_across_tournaments(self):
        game = create_test_game("Valorant")
        t1 = create_test_tournament(organizer=self.organizer, game=game)
        t2 = create_test_tournament(organizer=self.organizer, game=game)
        t3 = create_test_tournament(organizer=self.organizer, game=game)

        self.assertEqual(t1.game, game)
        self.assertEqual(t2.game, game)
        self.assertEqual(t3.game, game)
        self.assertEqual(Game.objects.filter(name="Valorant").count(), 1)

    def test_duplicate_tournament_names_unique_slugs(self):
        now = timezone.now()
        game = create_test_game("Dota 2")
        t1 = Tournament.objects.create(
            name="Champions Cup", game=game, organizer=self.organizer, description="D1", rules="R1",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION, team_size=5, max_participants=4,
            registration_start=now - timedelta(days=1), registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2), end_date=now + timedelta(days=5), contact_email="a@ex.com"
        )
        t2 = Tournament.objects.create(
            name="Champions Cup", game=game, organizer=self.organizer, description="D2", rules="R2",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION, team_size=5, max_participants=4,
            registration_start=now - timedelta(days=1), registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2), end_date=now + timedelta(days=5), contact_email="a@ex.com"
        )
        t3 = Tournament.objects.create(
            name="Champions Cup", game=game, organizer=self.organizer, description="D3", rules="R3",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION, team_size=5, max_participants=4,
            registration_start=now - timedelta(days=1), registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2), end_date=now + timedelta(days=5), contact_email="a@ex.com"
        )

        self.assertEqual(t1.slug, "champions-cup")
        self.assertEqual(t2.slug, "champions-cup-1")
        self.assertEqual(t3.slug, "champions-cup-2")
        self.assertEqual(Tournament.objects.filter(name="Champions Cup").count(), 3)

    def test_duplicate_team_name_rejected(self):
        Team.objects.create(name="Alpha Squad", manager=self.organizer)
        with self.assertRaises(IntegrityError):
            Team.objects.create(name="Alpha Squad", manager=self.organizer)

    def test_duplicate_username_rejected(self):
        with self.assertRaises(IntegrityError):
            User.objects.create_user(username="rule_player1", password="Password123!")

    def test_player_overlap_rules(self):
        player_a2 = User.objects.create_user(username="rule_player_a2", password="Password123!")
        # Same tournament, different teams with same player -> REJECT
        tourney1 = create_test_tournament(organizer=self.organizer, max_participants=4, team_size=2)

        team_a = Team.objects.create(name="Team A", manager=self.player1)
        TeamMember.objects.create(team=team_a, user=self.player1, team_role=TeamMember.TeamRole.MANAGER, is_active=True)
        TeamMember.objects.create(team=team_a, user=player_a2, team_role=TeamMember.TeamRole.PLAYER, is_active=True)

        team_b = Team.objects.create(name="Team B", manager=self.player2)
        TeamMember.objects.create(team=team_b, user=self.player2, team_role=TeamMember.TeamRole.MANAGER, is_active=True)
        TeamMember.objects.create(team=team_b, user=self.player1, team_role=TeamMember.TeamRole.PLAYER, is_active=True)

        res_a = register_team(tournament=tourney1, team=team_a, user=self.player1)
        self.assertTrue(res_a["success"], f"res_a failed: {res_a.get('message')}")

        res_b = register_team(tournament=tourney1, team=team_b, user=self.player2)
        self.assertFalse(res_b["success"])
        self.assertIn("already registered", res_b["message"].lower())

        # Different tournament with same player on Team B -> ALLOW
        tourney2 = create_test_tournament(organizer=self.organizer, max_participants=4, team_size=2)
        res_b_tourney2 = register_team(tournament=tourney2, team=team_b, user=self.player2)
        self.assertTrue(res_b_tourney2["success"], f"res_b_tourney2 failed: {res_b_tourney2.get('message')}")



    def test_solo_registration_behavior(self):
        tourney_solo = create_test_tournament(organizer=self.organizer, max_participants=4, team_size=1)
        tourney_solo.participation_type = Tournament.ParticipationType.SOLO
        tourney_solo.save()

        res = register_solo_player(tournament=tourney_solo, user=self.player1)
        self.assertTrue(res["success"])

        # Check Joined Tournaments logic
        joined_regs = TournamentRegistration.objects.filter(user=self.player1)
        self.assertTrue(joined_regs.exists())

        # Verify internal solo team is NOT listed under player's managed/joined teams
        managed_teams = Team.objects.filter(manager=self.player1, is_active=True)
        self.assertFalse(managed_teams.filter(slug__startswith="solo-team-").exists())


