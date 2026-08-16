from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase, Client
from django.urls import reverse

from apps.teams.forms import TeamCreateForm, TeamUpdateForm, TeamInvitationForm
from apps.teams.models import Team, TeamMember, TeamInvitation
from apps.teams.services import (
    create_team,
    update_team,
    send_team_invitation,
    accept_team_invitation,
    reject_team_invitation,
    get_team_profile_data,
)
from apps.notifications.models import Notification
from apps.tournaments.models import Game

User = get_user_model()


class TeamModelAndCrudTests(TestCase):
    """
    Tests Team creation, slug generation, manager constraints, and updating.
    """

    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(
            username="manager1",
            email="manager1@example.com",
            password="Password123!",
        )
        self.user2 = User.objects.create_user(
            username="player2",
            password="Password123!",
        )
        self.game = Game.objects.create(name="PUBG Mobile", slug="pubg-mobile-crud", is_active=True)

    def test_team_creation_service(self):
        form = TeamCreateForm(data={"name": "Team Phoenix", "game": self.game.pk, "description": "Rise above", "max_players": 5})
        self.assertTrue(form.is_valid(), form.errors)
        result = create_team(manager=self.manager, form=form)
        self.assertTrue(result["success"])
        team = result["team"]
        self.assertEqual(team.name, "Team Phoenix")
        self.assertEqual(team.slug, "team-phoenix")
        self.assertEqual(team.manager, self.manager)

        # Check manager auto-assigned as MANAGER member
        member = TeamMember.objects.get(team=team, user=self.manager)
        self.assertEqual(member.team_role, TeamMember.TeamRole.MANAGER)
        self.assertTrue(member.is_active)

    def test_manager_single_team_constraint(self):
        game2 = Game.objects.create(name="Valorant", slug="valorant-crud", is_active=True)
        form1 = TeamCreateForm(data={"name": "First Team", "game": self.game.pk, "description": "One", "max_players": 5})
        form1.is_valid()
        create_team(manager=self.manager, form=form1)

        # Creating a second team for the SAME game should fail
        form2 = TeamCreateForm(data={"name": "Second Team", "game": self.game.pk, "description": "Two", "max_players": 5})
        form2.is_valid()
        result2 = create_team(manager=self.manager, form=form2)
        self.assertFalse(result2["success"])
        self.assertIn("already manage a team", result2["message"])

        # Creating a team for a DIFFERENT game should succeed
        form3 = TeamCreateForm(data={"name": "Third Team", "game": game2.pk, "description": "Three", "max_players": 5})
        form3.is_valid()
        result3 = create_team(manager=self.manager, form=form3)
        self.assertTrue(result3["success"])

    def test_duplicate_team_name_db_constraint(self):
        Team.objects.create(name="Unique Name", manager=self.manager)
        with self.assertRaises(IntegrityError):
            Team.objects.create(name="Unique Name", manager=self.user2)

    def test_team_update_service(self):
        team = Team.objects.create(name="Old Name", description="Old desc", manager=self.manager)
        form = TeamUpdateForm(
            data={"name": "New Name", "description": "New desc", "max_players": 6, "is_active": True},
            instance=team,
        )
        self.assertTrue(form.is_valid())
        res = update_team(team=team, form=form)
        self.assertTrue(res["success"])
        team.refresh_from_db()
        self.assertEqual(team.name, "New Name")
        self.assertEqual(team.description, "New desc")
        self.assertEqual(team.max_players, 6)


class TeamMembershipAndActiveCountTests(TestCase):
    """
    Tests TeamMember relationship, unique constraint, and active_member_count invariants.
    """

    def setUp(self):
        self.manager = User.objects.create_user(username="mgr", password="Password123!")
        self.p1 = User.objects.create_user(username="p1", password="Password123!")
        self.p2 = User.objects.create_user(username="p2", password="Password123!")
        self.team = Team.objects.create(name="Warriors", manager=self.manager)
        TeamMember.objects.create(team=self.team, user=self.manager, team_role=TeamMember.TeamRole.MANAGER)

    def test_active_member_count_ignores_inactive_members(self):
        TeamMember.objects.create(team=self.team, user=self.p1, is_active=True)
        TeamMember.objects.create(team=self.team, user=self.p2, is_active=False)

        # Property test
        self.assertEqual(self.team.active_member_count, 2)  # manager + p1

        # Queryset annotation test as used in list views
        from django.db.models import Count, Q
        annotated_team = Team.objects.filter(id=self.team.id).annotate(
            _active_member_count=Count("members", filter=Q(members__is_active=True), distinct=True)
        ).first()
        self.assertEqual(annotated_team.active_member_count, 2)

    def test_duplicate_membership_db_constraint(self):
        with self.assertRaises(IntegrityError):
            TeamMember.objects.create(team=self.team, user=self.manager)


class TeamInvitationServiceTests(TestCase):
    """
    Tests team invitation workflows and permissions.
    """

    def setUp(self):
        self.manager = User.objects.create_user(username="lead", password="Password123!")
        self.other_user = User.objects.create_user(username="other", password="Password123!")
        self.player = User.objects.create_user(username="recruit", password="Password123!")
        self.team = Team.objects.create(name="Falcons", manager=self.manager)
        TeamMember.objects.create(team=self.team, user=self.manager)

    def test_send_invitation_success(self):
        res = send_team_invitation(team=self.team, sender=self.manager, receiver=self.player)
        self.assertTrue(res["success"])
        invitation = res["invitation"]
        self.assertEqual(invitation.status, TeamInvitation.Status.PENDING)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.player,
                notification_type=Notification.Type.TEAM_INVITATION,
            ).exists()
        )

    def test_send_invitation_by_non_manager_rejected(self):
        res = send_team_invitation(team=self.team, sender=self.other_user, receiver=self.player)
        self.assertFalse(res["success"])
        self.assertEqual(res["message"], "Only the team manager can invite players.")

    def test_send_duplicate_invitation_rejected(self):
        send_team_invitation(team=self.team, sender=self.manager, receiver=self.player)
        res2 = send_team_invitation(team=self.team, sender=self.manager, receiver=self.player)
        self.assertFalse(res2["success"])
        self.assertEqual(res2["message"], "A pending invitation already exists.")

    def test_send_invitation_to_existing_member_rejected(self):
        TeamMember.objects.create(team=self.team, user=self.player, is_active=True)
        res = send_team_invitation(team=self.team, sender=self.manager, receiver=self.player)
        self.assertFalse(res["success"])
        self.assertEqual(res["message"], "User is already a team member.")

    def test_accept_invitation(self):
        res = send_team_invitation(team=self.team, sender=self.manager, receiver=self.player)
        invitation = res["invitation"]
        accept_team_invitation(invitation=invitation)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, TeamInvitation.Status.ACCEPTED)
        self.assertTrue(TeamMember.objects.filter(team=self.team, user=self.player, is_active=True).exists())

    def test_reject_invitation(self):
        res = send_team_invitation(team=self.team, sender=self.manager, receiver=self.player)
        invitation = res["invitation"]
        reject_team_invitation(invitation=invitation)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, TeamInvitation.Status.REJECTED)
        self.assertFalse(TeamMember.objects.filter(team=self.team, user=self.player).exists())


class TeamViewAndPermissionTests(TestCase):
    """
    Tests team HTTP views and security permissions.
    """

    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(username="tmanager", password="Password123!")
        self.attacker = User.objects.create_user(username="attacker", password="Password123!")
        self.team = Team.objects.create(name="Dragons", manager=self.manager)
        TeamMember.objects.create(team=self.team, user=self.manager)

    def test_team_detail_public(self):
        url = reverse("teams:detail", kwargs={"slug": self.team.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dragons")

    def test_team_invite_view_non_manager_redirects(self):
        self.client.login(username="attacker", password="Password123!")
        url = reverse("teams:invite", kwargs={"slug": self.team.slug})
        response = self.client.get(url)
        self.assertRedirects(response, reverse("teams:detail", kwargs={"slug": self.team.slug}))

    def test_team_profile_data_stats(self):
        data = get_team_profile_data(team=self.team)
        self.assertEqual(data["team"], self.team)
        self.assertEqual(data["captain"], self.manager)
        self.assertEqual(data["wins"], 0)
        self.assertEqual(data["losses"], 0)


class TeamMemberCapacityRegressionTests(TestCase):
    """
    Regression tests verifying max_players team capacity enforcement during invitation sending and acceptance.
    """

    def setUp(self):
        self.manager = User.objects.create_user(username="cap_mgr", password="Password123!")
        # Create team with max_players = 3
        self.team = Team.objects.create(name="CapTeam", manager=self.manager, max_players=3)
        # Manager is member #1
        TeamMember.objects.create(team=self.team, user=self.manager, team_role=TeamMember.TeamRole.MANAGER, is_active=True)

        self.p1 = User.objects.create_user(username="cap_p1", password="Password123!")
        self.p2 = User.objects.create_user(username="cap_p2", password="Password123!")
        self.p3 = User.objects.create_user(username="cap_p3", password="Password123!")

    def test_team_below_capacity_invitation_accepted(self):
        # Current active members = 1 (manager). max_players = 3.
        inv_res = send_team_invitation(team=self.team, sender=self.manager, receiver=self.p1)
        self.assertTrue(inv_res["success"])
        invitation = inv_res["invitation"]

        acc_res = accept_team_invitation(invitation)
        self.assertTrue(acc_res["success"])
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, TeamInvitation.Status.ACCEPTED)
        self.assertEqual(self.team.active_member_count, 2)

    def test_team_one_member_below_capacity_accepted(self):
        # Add member #2 (so team has 2 active members out of max 3)
        TeamMember.objects.create(team=self.team, user=self.p1, is_active=True)
        self.assertEqual(self.team.active_member_count, 2)

        inv_res = send_team_invitation(team=self.team, sender=self.manager, receiver=self.p2)
        self.assertTrue(inv_res["success"])
        invitation = inv_res["invitation"]

        acc_res = accept_team_invitation(invitation)
        self.assertTrue(acc_res["success"])
        self.assertEqual(self.team.active_member_count, 3)

    def test_team_exactly_at_capacity_invitation_rejected(self):
        # Fill team to capacity (3 members: manager, p1, p2)
        TeamMember.objects.create(team=self.team, user=self.p1, is_active=True)
        TeamMember.objects.create(team=self.team, user=self.p2, is_active=True)
        self.assertEqual(self.team.active_member_count, 3)

        # Create invitation directly or before reaching full capacity
        invitation = TeamInvitation.objects.create(
            team=self.team,
            sender=self.manager,
            receiver=self.p3,
            status=TeamInvitation.Status.PENDING
        )
        notif = Notification.objects.create(
            recipient=self.p3,
            title="Team Invitation",
            message="Join team",
            notification_type=Notification.Type.TEAM_INVITATION,
            team_invitation=invitation
        )

        acc_res = accept_team_invitation(invitation)
        self.assertFalse(acc_res["success"])
        self.assertEqual(acc_res["message"], "Team has reached maximum player capacity.")

        # Assert no active TeamMember created
        self.assertFalse(TeamMember.objects.filter(team=self.team, user=self.p3).exists())
        self.assertEqual(self.team.active_member_count, 3)

        # Assert invitation status remains PENDING and notification unread
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, TeamInvitation.Status.PENDING)
        notif.refresh_from_db()
        self.assertFalse(notif.is_read)

    def test_send_invitation_at_capacity_rejected(self):
        # Fill team to capacity (3 members)
        TeamMember.objects.create(team=self.team, user=self.p1, is_active=True)
        TeamMember.objects.create(team=self.team, user=self.p2, is_active=True)
        self.assertEqual(self.team.active_member_count, 3)

        inv_res = send_team_invitation(team=self.team, sender=self.manager, receiver=self.p3)
        self.assertFalse(inv_res["success"])
        self.assertEqual(inv_res["message"], "Team has reached maximum player capacity.")

    def test_inactive_members_do_not_consume_active_capacity(self):
        # Add 1 active member (manager + p1 = 2 active) and 5 inactive members
        TeamMember.objects.create(team=self.team, user=self.p1, is_active=True)
        for i in range(5):
            u = User.objects.create_user(username=f"inact_{i}", password="Password123!")
            TeamMember.objects.create(team=self.team, user=u, is_active=False)

        # Active count must be 2, so team is NOT at max_players (3)
        self.assertEqual(self.team.active_member_count, 2)

        inv_res = send_team_invitation(team=self.team, sender=self.manager, receiver=self.p2)
        self.assertTrue(inv_res["success"])
        acc_res = accept_team_invitation(inv_res["invitation"])
        self.assertTrue(acc_res["success"])
        self.assertEqual(self.team.active_member_count, 3)


class UserAutocompleteAndTeamCreationTests(TestCase):
    """
    Tests for UserAutocompleteView endpoints, permissions, exclusions, security, and Team Creation page.
    """

    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(username="autocomp_mgr", password="Password123!")
        self.player_member = User.objects.create_user(username="autocomp_member", password="Password123!")
        self.player_pending = User.objects.create_user(username="autocomp_pending", password="Password123!")
        self.player_candidate1 = User.objects.create_user(username="alpha_player", password="Password123!")
        self.player_candidate2 = User.objects.create_user(username="ALPHA_HERO", password="Password123!")
        self.other_manager = User.objects.create_user(username="other_mgr", password="Password123!")

        self.team = Team.objects.create(name="Autocomplete Squad", manager=self.manager)
        TeamMember.objects.create(team=self.team, user=self.manager, team_role=TeamMember.TeamRole.MANAGER, is_active=True)
        TeamMember.objects.create(team=self.team, user=self.player_member, team_role=TeamMember.TeamRole.PLAYER, is_active=True)

        # Pending invitation
        TeamInvitation.objects.create(
            team=self.team,
            sender=self.manager,
            receiver=self.player_pending,
            status=TeamInvitation.Status.PENDING,
        )

    def test_unauthenticated_autocomplete_rejected(self):
        url = reverse("api:user_autocomplete", kwargs={"slug": self.team.slug})
        response = self.client.get(url, {"q": "alpha"})
        self.assertIn(response.status_code, [302, 401, 403])

    def test_non_manager_autocomplete_forbidden(self):
        self.client.login(username="other_mgr", password="Password123!")
        url = reverse("api:user_autocomplete", kwargs={"slug": self.team.slug})
        response = self.client.get(url, {"q": "alpha"})
        self.assertEqual(response.status_code, 403)

    def test_manager_autocomplete_success(self):
        self.client.login(username="autocomp_mgr", password="Password123!")
        url = reverse("api:user_autocomplete", kwargs={"slug": self.team.slug})
        response = self.client.get(url, {"q": "alpha"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(isinstance(data, list))
        usernames = [u["username"] for u in data]
        self.assertIn("alpha_player", usernames)
        self.assertIn("ALPHA_HERO", usernames)

    def test_autocomplete_exclusions(self):
        self.client.login(username="autocomp_mgr", password="Password123!")
        url = reverse("api:user_autocomplete", kwargs={"slug": self.team.slug})

        # Query for all users
        response = self.client.get(url, {"q": "a"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        usernames = [u["username"] for u in data]

        # Manager, existing active member, and pending invitee MUST be excluded
        self.assertNotIn("autocomp_mgr", usernames)
        self.assertNotIn("autocomp_member", usernames)
        self.assertNotIn("autocomp_pending", usernames)

    def test_autocomplete_security_no_sensitive_fields(self):
        self.client.login(username="autocomp_mgr", password="Password123!")
        url = reverse("api:user_autocomplete", kwargs={"slug": self.team.slug})
        response = self.client.get(url, {"q": "alpha"})
        data = response.json()
        self.assertTrue(len(data) > 0)
        user_item = data[0]
        # Only id and username allowed
        self.assertEqual(set(user_item.keys()), {"id", "username"})

    def test_autocomplete_result_limit(self):
        self.client.login(username="autocomp_mgr", password="Password123!")
        # Create 15 matching users
        for i in range(15):
            User.objects.create_user(username=f"limit_user_{i}", password="Password123!")

        url = reverse("api:user_autocomplete", kwargs={"slug": self.team.slug})
        response = self.client.get(url, {"q": "limit_user"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertLessEqual(len(data), 10)

    def test_team_creation_page_get(self):
        new_mgr = User.objects.create_user(username="fresh_mgr", password="Password123!")
        self.client.login(username="fresh_mgr", password="Password123!")
        url = reverse("teams:create")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "teams/create_team.html")

    def test_team_creation_page_post_success(self):
        game = Game.objects.create(name="Test Game Post", slug="test-game-post", is_active=True)
        new_mgr = User.objects.create_user(username="fresh_mgr2", password="Password123!")
        self.client.login(username="fresh_mgr2", password="Password123!")
        url = reverse("teams:create")
        post_data = {
            "name": "Brand New Team",
            "game": game.pk,
            "description": "Awesome team description",
            "max_players": 5,
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Team.objects.filter(name="Brand New Team", manager=new_mgr).exists())


class RemoveTeamMemberTests(TestCase):
    """
    Tests for the Remove Player (RemoveTeamMemberView) feature.
    """

    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(username="rm_manager", password="Password123!")
        self.player = User.objects.create_user(username="rm_player", password="Password123!")
        self.outsider = User.objects.create_user(username="rm_outsider", password="Password123!")

        self.team = Team.objects.create(name="Removal Test Team", manager=self.manager)
        TeamMember.objects.create(team=self.team, user=self.manager, team_role=TeamMember.TeamRole.MANAGER, is_active=True)
        self.membership = TeamMember.objects.create(team=self.team, user=self.player, team_role=TeamMember.TeamRole.PLAYER, is_active=True)

    def _remove_url(self, user_id=None):
        uid = user_id or self.player.pk
        return reverse("teams:remove_member", kwargs={"slug": self.team.slug, "member_id": uid})

    def test_manager_can_remove_player(self):
        self.client.login(username="rm_manager", password="Password123!")
        response = self.client.post(self._remove_url())
        self.assertEqual(response.status_code, 302)
        self.membership.refresh_from_db()
        self.assertFalse(self.membership.is_active)
        self.assertIsNotNone(self.membership.left_at)

    def test_non_manager_gets_403(self):
        self.client.login(username="rm_outsider", password="Password123!")
        response = self.client.post(self._remove_url())
        self.assertEqual(response.status_code, 403)
        self.membership.refresh_from_db()
        self.assertTrue(self.membership.is_active)

    def test_manager_cannot_remove_themselves(self):
        from apps.teams.services import remove_team_member
        result = remove_team_member(team=self.team, manager=self.manager, member_user=self.manager)
        self.assertFalse(result["success"])
        self.assertIn("manager cannot remove", result["message"].lower())

    def test_removed_member_excluded_from_active_count(self):
        self.assertEqual(self.team.active_member_count, 2)
        self.membership.is_active = False
        self.membership.save()
        team = Team.objects.get(pk=self.team.pk)
        self.assertEqual(team.active_member_count, 1)

    def test_remove_nonexistent_member_returns_error(self):
        from apps.teams.services import remove_team_member
        ghost = User.objects.create_user(username="ghost_user_rm", password="Password123!")
        result = remove_team_member(team=self.team, manager=self.manager, member_user=ghost)
        self.assertFalse(result["success"])
        self.assertIn("not an active member", result["message"].lower())


class MyTeamsAndJoinedTeamsViewTests(TestCase):
    """
    Tests that MyTeamsView shows only managed teams and
    JoinedTeamsView shows only joined-not-managed teams.
    """

    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(username="view_mgr", password="Password123!")
        self.player = User.objects.create_user(username="view_player", password="Password123!")
        self.other_manager = User.objects.create_user(username="other_mgr_vt", password="Password123!")

        self.managed_team = Team.objects.create(name="Managed Team View", manager=self.manager)
        TeamMember.objects.create(team=self.managed_team, user=self.manager, team_role=TeamMember.TeamRole.MANAGER, is_active=True)

        self.joined_team = Team.objects.create(name="Joined Team View", manager=self.other_manager)
        TeamMember.objects.create(team=self.joined_team, user=self.other_manager, team_role=TeamMember.TeamRole.MANAGER, is_active=True)
        TeamMember.objects.create(team=self.joined_team, user=self.player, team_role=TeamMember.TeamRole.PLAYER, is_active=True)

    def test_my_teams_only_shows_managed(self):
        self.client.login(username="view_mgr", password="Password123!")
        response = self.client.get(reverse("teams:list"))
        self.assertEqual(response.status_code, 200)
        teams = list(response.context["teams"])
        self.assertIn(self.managed_team, teams)
        self.assertNotIn(self.joined_team, teams)

    def test_joined_teams_only_shows_joined_not_managed(self):
        self.client.login(username="view_player", password="Password123!")
        response = self.client.get(reverse("teams:joined"))
        self.assertEqual(response.status_code, 200)
        teams = list(response.context["teams"])
        self.assertIn(self.joined_team, teams)
        self.assertNotIn(self.managed_team, teams)

    def test_joined_teams_does_not_show_managed_teams(self):
        self.client.login(username="view_mgr", password="Password123!")
        response = self.client.get(reverse("teams:joined"))
        self.assertEqual(response.status_code, 200)
        teams = list(response.context["teams"])
        self.assertNotIn(self.managed_team, teams)

    def test_joined_teams_unauthenticated_redirects(self):
        response = self.client.get(reverse("teams:joined"))
        self.assertEqual(response.status_code, 302)


class SettingsViewTests(TestCase):
    """
    Tests for the account settings and password change views.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="settings_user",
            email="settings@example.com",
            password="Password123!",
        )

    def test_settings_unauthenticated_redirects(self):
        response = self.client.get(reverse("accounts:settings"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_settings_authenticated_200(self):
        self.client.login(username="settings_user", password="Password123!")
        response = self.client.get(reverse("accounts:settings"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/settings.html")

    def test_password_change_get_authenticated(self):
        self.client.login(username="settings_user", password="Password123!")
        response = self.client.get(reverse("accounts:password_change"))
        self.assertEqual(response.status_code, 200)

    def test_password_change_flow(self):
        self.client.login(username="settings_user", password="Password123!")
        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": "Password123!",
                "new_password1": "N3wS3cur3Pass!",
                "new_password2": "N3wS3cur3Pass!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("done", response.url)
