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
    generate_single_elimination_bracket,
    advance_winner,
    get_tournament_statistics,
)

User = get_user_model()


def create_test_game(name="Valorant"):
    return Game.objects.create(name=name, description="FPS Game")


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
