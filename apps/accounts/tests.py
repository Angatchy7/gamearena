from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase, Client
from django.urls import reverse

from apps.accounts.forms import UserRegistrationForm
from apps.accounts.services import get_player_profile
from apps.teams.models import Team, TeamMember
from apps.tournaments.models import Game, Tournament, Round, Match, TournamentRegistration
from django.utils import timezone
import datetime

User = get_user_model()


class UserRegistrationTests(TestCase):
    """
    Tests user creation, registration form, validation, and role assignment.
    """

    def setUp(self):
        self.client = Client()

    def test_valid_user_creation(self):
        user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="Password123!",
        )
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "testuser@example.com")
        self.assertEqual(user.role, User.Role.USER)
        self.assertTrue(user.check_password("Password123!"))

    def test_admin_user_creation(self):
        admin = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="AdminPassword123!",
            role=User.Role.ADMIN,
        )
        self.assertEqual(admin.role, User.Role.ADMIN)

    def test_registration_form_valid(self):
        form_data = {
            "username": "newplayer",
            "email": "newplayer@example.com",
            "password1": "SecurePass123!",
            "password2": "SecurePass123!",
        }
        form = UserRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.role, User.Role.USER)

    def test_registration_form_duplicate_username(self):
        User.objects.create_user(username="duplicate", password="Password123!")
        form_data = {
            "username": "duplicate",
            "email": "diff@example.com",
            "password1": "Password123!",
            "password2": "Password123!",
        }
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_registration_form_password_mismatch(self):
        form_data = {
            "username": "mismatch",
            "email": "mismatch@example.com",
            "password1": "Password123!",
            "password2": "Different123!",
        }
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_registration_view_post_success(self):
        url = reverse("accounts:register")
        post_data = {
            "username": "registereduser",
            "email": "reg@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }
        response = self.client.post(url, post_data)
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertTrue(User.objects.filter(username="registereduser").exists())


class AuthenticationViewTests(TestCase):
    """
    Tests login, logout, and redirection logic.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="authuser",
            email="authuser@example.com",
            password="CorrectPassword123!",
        )

    def test_login_valid_credentials(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "authuser", "password": "CorrectPassword123!"},
        )
        self.assertRedirects(response, "/dashboard/")

    def test_login_invalid_password(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "authuser", "password": "WrongPassword!"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct")

    def test_login_nonexistent_user(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "nobody", "password": "SomePassword123!"},
        )
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        self.client.login(username="authuser", password="CorrectPassword123!")
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("accounts:login"))


class SecurityAndRolePermissionTests(TestCase):
    """
    Tests role-based permission enforcement and unauthenticated access control.
    """

    def setUp(self):
        self.client = Client()
        self.normal_user = User.objects.create_user(
            username="player_user",
            password="Password123!",
            role=User.Role.USER,
        )
        self.admin_user = User.objects.create_user(
            username="admin_user",
            password="Password123!",
            role=User.Role.ADMIN,
        )

    def test_unauthenticated_protected_page_access(self):
        protected_urls = [
            reverse("dashboard:home"),
            reverse("teams:create"),
            reverse("tournaments:create"),
        ]
        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("accounts:login"), response.url)

    def test_normal_user_admin_dashboard_denied(self):
        self.client.login(username="player_user", password="Password123!")
        response = self.client.get(reverse("dashboard:admin"))
        self.assertEqual(response.status_code, 403)

    def test_admin_user_admin_dashboard_allowed(self):
        self.client.login(username="admin_user", password="Password123!")
        response = self.client.get(reverse("dashboard:admin"))
        self.assertEqual(response.status_code, 200)

    def test_player_profile_view_public(self):
        url = reverse("accounts:profile", kwargs={"username": self.normal_user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.normal_user.username)

    def test_player_profile_nonexistent_user_404(self):
        url = reverse("accounts:profile", kwargs={"username": "doesnotexist"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class PlayerProfileServiceTests(TestCase):
    """
    Tests get_player_profile computation logic.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="pro_player",
            password="Password123!",
        )
        self.team = Team.objects.create(
            name="Alpha Squad",
            manager=self.user,
        )
        TeamMember.objects.create(
            team=self.team,
            user=self.user,
            team_role=TeamMember.TeamRole.MANAGER,
            is_active=True,
        )

    def test_get_player_profile_basic(self):
        data = get_player_profile(user=self.user)
        self.assertEqual(data["player"], self.user)
        self.assertEqual(len(data["user_teams"]), 1)
        self.assertEqual(data["user_teams"][0], self.team)
        self.assertEqual(data["wins"], 0)
        self.assertEqual(data["losses"], 0)
        self.assertEqual(data["matches_played"], 0)
        self.assertEqual(data["win_rate"], 0.0)

    def test_get_player_profile_achievements(self):
        data = get_player_profile(user=self.user)
        achievement_titles = [a["title"] for a in data["achievements"]]
        self.assertIn("Team Leader", achievement_titles)
