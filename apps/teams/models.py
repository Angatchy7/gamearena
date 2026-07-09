from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Team(models.Model):
    """
    Represents an esports team.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    slug = models.SlugField(
        unique=True,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    logo = models.ImageField(
        upload_to="teams/logos/",
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_teams",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Team"
        verbose_name_plural = "Teams"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    """
    Represents a user's membership in a team.
    """

    class ManagementRole(models.TextChoices):
        CAPTAIN = "CAPTAIN", "Captain"
        PLAYER = "PLAYER", "Player"

    class GameRole(models.TextChoices):
        IGL = "IGL", "In-Game Leader"
        PLAYER = "PLAYER", "Player"

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="team_memberships",
    )

    management_role = models.CharField(
        max_length=10,
        choices=ManagementRole.choices,
        default=ManagementRole.PLAYER,
    )

    game_role = models.CharField(
        max_length=10,
        choices=GameRole.choices,
        default=GameRole.PLAYER,
    )

    joined_at = models.DateTimeField(
        auto_now_add=True,
    )

    left_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["team", "user"]
        verbose_name = "Team Membership"
        verbose_name_plural = "Team Memberships"

        constraints = [
            models.UniqueConstraint(
                fields=["team", "user"],
                name="unique_team_member",
            ),
        ]

    def __str__(self):
        return (
            f"{self.user.username} "
            f"({self.management_role}) "
            f"- {self.team.name}"
        )