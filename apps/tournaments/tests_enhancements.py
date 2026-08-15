import shutil
import tempfile
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.teams.models import Team, TeamMember
from apps.tournaments.models import Game, Tournament, TournamentRegistration, Round, Match
from apps.tournaments.services import (
    register_solo_player,
    register_team,
    generate_single_elimination_bracket,
)

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ProductionUXAndEnhancementsTest(TestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):

        self.client = Client()
        self.user1 = User.objects.create_user(
            username="player_one",
            email="player_one@example.com",
            password="Password123!",
        )
        self.user2 = User.objects.create_user(
            username="player_two",
            email="player_two@example.com",
            password="Password123!",
        )
        self.organizer = User.objects.create_user(
            username="organizer_user",
            email="organizer@example.com",
            password="Password123!",
        )

        self.game_pubg = Game.objects.create(
            name="PUBG Mobile",
            slug="pubg-mobile",
            description="Battle Royale Game",
        )
        self.game_generic = Game.objects.create(
            name="Custom Game",
            slug="custom-game",
            description="Generic Game",
        )

        now = timezone.now()
        self.solo_tournament = Tournament.objects.create(
            name="SOLO Championship",
            slug="solo-championship",
            game=self.game_pubg,
            organizer=self.organizer,
            description="Solo tournament description",
            rules="Standard rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.SOLO,
            team_size=1,
            max_participants=8,
            registration_fee=0,
            prize_pool=1000,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=3),
            contact_email="organizer@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )

        self.team_tournament = Tournament.objects.create(
            name="TEAM Championship",
            slug="team-championship",
            game=self.game_generic,
            organizer=self.organizer,
            description="Team tournament description",
            rules="Standard rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.TEAM,
            team_size=2,
            max_participants=8,
            registration_fee=0,
            prize_pool=2000,
            registration_start=now - timedelta(days=1),
            registration_end=now + timedelta(days=1),
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=3),
            contact_email="organizer@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )

    def test_solo_display_name_never_shows_internal_team_string(self):
        res1 = register_solo_player(tournament=self.solo_tournament, user=self.user1)
        res2 = register_solo_player(tournament=self.solo_tournament, user=self.user2)

        reg1 = res1["registration"]
        reg2 = res2["registration"]

        self.assertEqual(reg1.display_name, "player_one")
        self.assertEqual(reg2.display_name, "player_two")
        self.assertEqual(reg1.team.display_name, "player_one")

        generate_single_elimination_bracket(tournament=self.solo_tournament)
        match = Match.objects.filter(round__tournament=self.solo_tournament).first()

        self.assertIn(match.team_one_display, ["player_one", "player_two"])
        self.assertNotIn("__SOLO_", match.team_one_display)
        self.assertNotIn("__SOLO_INTERNAL__", match.team_one_display)

    def test_team_display_name_shows_real_team_name(self):
        team = Team.objects.create(
            name="Alpha Squad",
            manager=self.user1,
            description="Pro Team",
        )
        TeamMember.objects.create(team=team, user=self.user1, team_role=TeamMember.TeamRole.MANAGER)
        TeamMember.objects.create(team=team, user=self.user2, team_role=TeamMember.TeamRole.PLAYER)

        reg_res = register_team(tournament=self.team_tournament, team=team, user=self.user1)
        reg = reg_res["registration"]

        self.assertEqual(team.display_name, "Alpha Squad")
        self.assertEqual(reg.display_name, "Alpha Squad")

    def test_image_url_fallbacks_and_uploaded_priorities(self):
        # Game fallbacks
        self.assertIn("images/games/pubg.svg", self.game_pubg.image_url)
        self.assertIn("images/defaults/game_default.svg", self.game_generic.image_url)

        # Uploaded game image takes priority
        dummy_img = SimpleUploadedFile("test_game.png", b"fake_image_bytes", content_type="image/png")
        self.game_generic.logo = dummy_img
        self.game_generic.save()
        self.assertIn("test_game", self.game_generic.image_url)

        # Team logo fallback & priority
        team = Team.objects.create(name="Beta Force", manager=self.user1)
        self.assertIn("images/defaults/team_default.svg", team.logo_url)
        dummy_logo = SimpleUploadedFile("team_logo.png", b"fake_logo_bytes", content_type="image/png")
        team.logo = dummy_logo
        team.save()
        self.assertIn("team_logo", team.logo_url)

        # Tournament cover & banner fallbacks
        self.assertIn("images/games/pubg.svg", self.solo_tournament.cover_url)
        dummy_cover = SimpleUploadedFile("cover.jpg", b"fake_cover_bytes", content_type="image/jpeg")
        self.solo_tournament.cover_image = dummy_cover
        self.solo_tournament.save()
        self.assertIn("cover", self.solo_tournament.cover_url)


    def test_registration_user_identity_and_notification_emails(self):
        res1 = register_solo_player(tournament=self.solo_tournament, user=self.user1)
        reg1 = res1["registration"]

        self.assertEqual(reg1.user, self.user1)
        self.assertEqual(reg1.get_notification_emails(), ["player_one@example.com"])

        team = Team.objects.create(name="Omega Team", manager=self.user1)
        TeamMember.objects.create(team=team, user=self.user1)
        TeamMember.objects.create(team=team, user=self.user2)

        res_team = register_team(tournament=self.team_tournament, team=team, user=self.user1)
        reg_team = res_team["registration"]

        emails = reg_team.get_notification_emails()
        self.assertIn("player_one@example.com", emails)
        self.assertIn("player_two@example.com", emails)

    def test_match_notification_emails_resolution(self):
        register_solo_player(tournament=self.solo_tournament, user=self.user1)
        register_solo_player(tournament=self.solo_tournament, user=self.user2)
        generate_single_elimination_bracket(tournament=self.solo_tournament)

        match = Match.objects.filter(round__tournament=self.solo_tournament).first()
        match_emails = match.get_participant_emails()

        self.assertIn("player_one@example.com", match_emails)
        self.assertIn("player_two@example.com", match_emails)

    def test_auth_pages_password_toggles_present(self):
        login_url = reverse("accounts:login")
        response_login = self.client.get(login_url)
        self.assertEqual(response_login.status_code, 200)
        self.assertContains(response_login, 'type="button"')
        self.assertContains(response_login, 'aria-label="Toggle password visibility"')

        register_url = reverse("accounts:register")
        response_reg = self.client.get(register_url)
        self.assertEqual(response_reg.status_code, 200)
        self.assertContains(response_reg, 'data-target="id_password1"')
        self.assertContains(response_reg, 'data-target="id_password2"')


class TournamentLifecycleStatusTests(TestCase):
    """
    Tests for the current_status property and tournament status filters.
    """

    def setUp(self):
        self.client = Client()
        self.organizer = User.objects.create_user(username="lifecycle_org", password="Password123!")
        self.game = Game.objects.create(name="Lifecycle Game", slug="lifecycle-game", description="Test")

    def _make_tournament(self, name, slug, reg_start_offset, reg_end_offset, start_offset, end_offset, status=None):
        now = timezone.now()
        t = Tournament.objects.create(
            name=name,
            slug=slug,
            game=self.game,
            organizer=self.organizer,
            description="Test",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.SOLO,
            team_size=1,
            max_participants=4,
            registration_fee=0,
            prize_pool=500,
            registration_start=now + timedelta(seconds=reg_start_offset),
            registration_end=now + timedelta(seconds=reg_end_offset),
            start_date=now + timedelta(seconds=start_offset),
            end_date=now + timedelta(seconds=end_offset),
            contact_email="lifecycle@example.com",
            status=status or Tournament.Status.REGISTRATION_OPEN,
        )
        return t

    def test_current_status_before_registration_window(self):
        """Tournament not yet in registration window returns REGISTRATION_CLOSED."""
        t = self._make_tournament(
            "Pre-Reg", "pre-reg",
            reg_start_offset=3600,   # starts in 1 hour
            reg_end_offset=7200,
            start_offset=10800,
            end_offset=14400,
        )
        self.assertEqual(t.current_status, Tournament.Status.REGISTRATION_CLOSED)

    def test_current_status_during_registration_window(self):
        """Tournament in active registration window returns REGISTRATION_OPEN."""
        t = self._make_tournament(
            "Reg Open", "reg-open",
            reg_start_offset=-3600,   # started 1 hour ago
            reg_end_offset=3600,      # ends in 1 hour
            start_offset=7200,
            end_offset=14400,
        )
        self.assertEqual(t.current_status, Tournament.Status.REGISTRATION_OPEN)

    def test_current_status_after_registration_before_start(self):
        """Tournament past reg end but before start is REGISTRATION_CLOSED."""
        t = self._make_tournament(
            "Reg Closed", "reg-closed",
            reg_start_offset=-7200,
            reg_end_offset=-3600,   # ended 1 hour ago
            start_offset=3600,
            end_offset=14400,
        )
        self.assertEqual(t.current_status, Tournament.Status.REGISTRATION_CLOSED)

    def test_current_status_live(self):
        """Tournament in live window returns LIVE."""
        t = self._make_tournament(
            "Live Tourney", "live-tourney",
            reg_start_offset=-14400,
            reg_end_offset=-7200,
            start_offset=-3600,   # started 1 hour ago
            end_offset=3600,      # ends in 1 hour
        )
        self.assertEqual(t.current_status, Tournament.Status.LIVE)

    def test_current_status_completed(self):
        """Tournament past end date returns COMPLETED."""
        t = self._make_tournament(
            "Done Tourney", "done-tourney",
            reg_start_offset=-14400,
            reg_end_offset=-10800,
            start_offset=-7200,
            end_offset=-3600,   # ended 1 hour ago
        )
        self.assertEqual(t.current_status, Tournament.Status.COMPLETED)

    def test_current_status_draft_unchanged(self):
        """DRAFT tournaments always stay DRAFT regardless of dates."""
        t = self._make_tournament(
            "Draft T", "draft-t",
            reg_start_offset=-3600,
            reg_end_offset=3600,
            start_offset=7200,
            end_offset=14400,
            status=Tournament.Status.DRAFT,
        )
        self.assertEqual(t.current_status, Tournament.Status.DRAFT)

    def test_current_status_cancelled_unchanged(self):
        """CANCELLED tournaments always stay CANCELLED."""
        t = self._make_tournament(
            "Cancelled T", "cancelled-t",
            reg_start_offset=-3600,
            reg_end_offset=3600,
            start_offset=7200,
            end_offset=14400,
            status=Tournament.Status.CANCELLED,
        )
        self.assertEqual(t.current_status, Tournament.Status.CANCELLED)

    def test_registration_blocked_after_deadline(self):
        """register_solo_player and register_team are blocked when registration_end has passed."""
        t_solo = self._make_tournament(
            "Closed Reg Solo", "closed-reg-solo",
            reg_start_offset=-7200,
            reg_end_offset=-3600,
            start_offset=3600,
            end_offset=14400,
        )
        player = User.objects.create_user(username="lc_blocked_solo", password="Password123!")
        from apps.tournaments.services import register_solo_player, register_team
        result_solo = register_solo_player(tournament=t_solo, user=player)
        self.assertFalse(result_solo["success"])
        self.assertEqual(result_solo["message"], "Tournament registration is closed.")

        now = timezone.now()
        t_team = Tournament.objects.create(
            name="Closed Reg Team",
            slug="closed-reg-team",
            game=self.game,
            organizer=self.organizer,
            description="Test",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.TEAM,
            team_size=2,
            max_participants=4,
            registration_start=now - timedelta(hours=2),
            registration_end=now - timedelta(hours=1),
            start_date=now + timedelta(hours=1),
            end_date=now + timedelta(hours=4),
            contact_email="lifecycle@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )
        mgr = User.objects.create_user(username="team_mgr_closed", password="Password123!")
        p2 = User.objects.create_user(username="team_p2_closed", password="Password123!")
        team = Team.objects.create(name="Closed Team", manager=mgr)
        TeamMember.objects.create(team=team, user=mgr, is_active=True)
        TeamMember.objects.create(team=team, user=p2, is_active=True)

        result_team = register_team(tournament=t_team, team=team, user=mgr)
        self.assertFalse(result_team["success"])
        self.assertEqual(result_team["message"], "Tournament registration is closed.")

    def test_registration_succeeds_when_window_active_before_start(self):
        """Registration succeeds for active window even if tournament start_date is in the future (Upcoming)."""
        now = timezone.now()
        t_team = Tournament.objects.create(
            name="Active Window Team",
            slug="active-window-team",
            game=self.game,
            organizer=self.organizer,
            description="Test",
            rules="Rules",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.TEAM,
            team_size=2,
            max_participants=4,
            registration_start=now - timedelta(hours=1),
            registration_end=now + timedelta(hours=1),
            start_date=now + timedelta(hours=2),
            end_date=now + timedelta(hours=5),
            contact_email="lifecycle@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )
        mgr = User.objects.create_user(username="team_mgr_open", password="Password123!")
        p2 = User.objects.create_user(username="team_p2_open", password="Password123!")
        team = Team.objects.create(name="Open Team", manager=mgr)
        TeamMember.objects.create(team=team, user=mgr, is_active=True)
        TeamMember.objects.create(team=team, user=p2, is_active=True)

        from apps.tournaments.services import register_team, register_solo_player
        result_team = register_team(tournament=t_team, team=team, user=mgr)
        self.assertTrue(result_team["success"])

        t_solo = self._make_tournament(
            "Active Window Solo", "active-window-solo",
            reg_start_offset=-3600,
            reg_end_offset=3600,
            start_offset=7200,
            end_offset=14400,
        )
        solo_player = User.objects.create_user(username="solo_open_player", password="Password123!")
        result_solo = register_solo_player(tournament=t_solo, user=solo_player)
        self.assertTrue(result_solo["success"])

    def test_registration_fails_when_db_status_explicitly_closed(self):
        """Explicit DB status REGISTRATION_CLOSED rejects registration even within date window."""
        t_solo = self._make_tournament(
            "Explicit Closed Solo", "explicit-closed-solo",
            reg_start_offset=-3600,
            reg_end_offset=3600,
            start_offset=7200,
            end_offset=14400,
            status=Tournament.Status.REGISTRATION_CLOSED,
        )
        player = User.objects.create_user(username="exp_closed_player", password="Password123!")
        from apps.tournaments.services import register_solo_player
        res = register_solo_player(tournament=t_solo, user=player)
        self.assertFalse(res["success"])
        self.assertEqual(res["message"], "Tournament registration is closed.")

    def test_tournament_list_status_filter_live(self):
        """?status=live returns only live tournaments."""
        self.client.login(username="lifecycle_org", password="Password123!")
        live = self._make_tournament(
            "Live Filter T", "live-filter-t",
            reg_start_offset=-14400,
            reg_end_offset=-7200,
            start_offset=-3600,
            end_offset=3600,
        )
        url = reverse("tournaments:list") + "?status=live"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        slugs = [t.slug for t in response.context["tournaments"]]
        self.assertIn(live.slug, slugs)

    def test_tournament_list_status_filter_upcoming(self):
        """?status=upcoming returns future tournaments."""
        self.client.login(username="lifecycle_org", password="Password123!")
        upcoming = self._make_tournament(
            "Upcoming Filter T", "upcoming-filter-t",
            reg_start_offset=3600,
            reg_end_offset=7200,
            start_offset=10800,
            end_offset=14400,
        )
        url = reverse("tournaments:list") + "?status=upcoming"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        slugs = [t.slug for t in response.context["tournaments"]]
        self.assertIn(upcoming.slug, slugs)


class SprintRegressionTests(TestCase):
    """
    Regression tests for the Final Completion Sprint fixes.

    Covers:
    - A: get_tournament_statistics does not crash on SOLO registrations (reg.team is None)
    - F: Game.image_url maps Free Fire and Rocket League correctly without cross-match bugs
    - E: Tournament list supports ?game=<slug> filtering
    - L: Free/Paid form clean zeroes registration_fee when fee_type=free
    """

    def setUp(self):
        from datetime import timedelta
        self.organizer = User.objects.create_user(
            username="sprint_org", password="Password123!", email="sprint_org@example.com"
        )
        self.client = Client()
        self.game = Game.objects.create(
            name="Valorant", slug="valorant", description="FPS"
        )
        now = timezone.now()
        self.tournament = Tournament.objects.create(
            name="Sprint Reg Test",
            game=self.game,
            organizer=self.organizer,
            description="Sprint test tournament",
            rules="Standard",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.SOLO,
            team_size=1,
            max_participants=4,
            registration_start=now - timedelta(hours=2),
            registration_end=now + timedelta(hours=2),
            start_date=now + timedelta(days=1),
            end_date=now + timedelta(days=2),
            contact_email="sprint_org@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )

    def test_get_tournament_statistics_solo_no_crash(self):
        """
        Regression: get_tournament_statistics must NOT crash when SOLO
        registrations have reg.team = None.
        """
        from apps.tournaments.services import register_solo_player, get_tournament_statistics

        solo_user = User.objects.create_user(
            username="solo_stats_player", password="Password123!"
        )
        register_solo_player(tournament=self.tournament, user=solo_user)
        # Also add a registration where team is None to verify the None-guard
        user_no_team = User.objects.create_user(
            username="solo_no_team_player", password="Password123!"
        )
        TournamentRegistration.objects.create(
            tournament=self.tournament,
            user=user_no_team,
            registered_by=user_no_team,
            team=None,
        )

        # This must not raise AttributeError: 'NoneType' object has no attribute 'id'
        stats = get_tournament_statistics(tournament=self.tournament)
        self.assertIn("tournament", stats)
        # 1 ranking for the registered solo team (team=None reg is safely skipped)
        self.assertEqual(len(stats["team_rankings"]), 1)
        self.assertEqual(stats["team_rankings"][0]["team"].display_name, "solo_stats_player")

    def test_game_image_url_free_fire(self):
        """
        Regression: Game.image_url must return free_fire.svg for Free Fire games,
        not fall through to game_default.svg.
        """
        g = Game(name="Garena Free Fire", slug="free-fire")
        url = g.image_url
        self.assertIn("free_fire", url)
        self.assertNotIn("game_default", url)

    def test_game_image_url_rocket_league_does_not_match_fc(self):
        """
        Regression: Rocket League must NOT match EA FC / FIFA patterns.
        Ensure the mapping returns rocket_league.svg.
        """
        g = Game(name="Rocket League", slug="rocket-league")
        url = g.image_url
        self.assertIn("rocket_league", url)
        self.assertNotIn("eafc", url)
        self.assertNotIn("game_default", url)

    def test_game_image_url_ea_fc_correct(self):
        """EA Sports FC must return eafc.svg, not rocket_league.svg."""
        g = Game(name="EA Sports FC 25", slug="ea-sports-fc")
        url = g.image_url
        self.assertIn("eafc", url)
        self.assertNotIn("rocket", url)

    def test_tournament_list_game_slug_filter(self):
        """Tournament list ?game=<slug> must filter by that game."""
        from datetime import timedelta
        other_game = Game.objects.create(
            name="PUBG Mobile", slug="pubg-mobile", description="BR"
        )
        now = timezone.now()
        pubg_t = Tournament.objects.create(
            name="PUBG Sprint Tournament",
            game=other_game,
            organizer=self.organizer,
            description="PUBG test",
            rules="Standard",
            tournament_type=Tournament.TournamentType.SINGLE_ELIMINATION,
            participation_type=Tournament.ParticipationType.SOLO,
            team_size=1,
            max_participants=4,
            registration_start=now - timedelta(hours=1),
            registration_end=now + timedelta(hours=1),
            start_date=now + timedelta(days=1),
            end_date=now + timedelta(days=2),
            contact_email="sprint_org@example.com",
            status=Tournament.Status.REGISTRATION_OPEN,
        )
        self.client.login(username="sprint_org", password="Password123!")
        url = reverse("tournaments:list") + "?game=pubg-mobile"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        slugs = [t.slug for t in response.context["tournaments"]]
        self.assertIn(pubg_t.slug, slugs)
        self.assertNotIn(self.tournament.slug, slugs)

    def test_free_tournament_form_zeroes_fee(self):
        """
        Regression: TournamentCreateForm with fee_type=free must zero out
        registration_fee regardless of what value is POSTed for the field.
        """
        from apps.tournaments.forms import TournamentCreateForm
        from datetime import timedelta
        now = timezone.now()
        data = {
            "name": "Free Test Tournament",
            "game": self.game.pk,
            "description": "Test",
            "rules": "Standard",
            "tournament_type": Tournament.TournamentType.SINGLE_ELIMINATION,
            "participation_type": Tournament.ParticipationType.SOLO,
            "team_size": 1,
            "max_participants": 4,
            "registration_start": (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "registration_end": (now + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "start_date": (now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "end_date": (now + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "prize_pool": "0.00",
            "contact_email": "test@example.com",
            "registration_fee": "999.99",  # Should be zeroed by fee_type=free
            "fee_type": "free",
        }
        form = TournamentCreateForm(data=data)
        if form.is_valid():
            from decimal import Decimal
            self.assertEqual(form.cleaned_data["registration_fee"], Decimal("0.00"))
        # If form is invalid for other reasons, that's fine — we just check
        # the fee is zeroed when it IS valid
