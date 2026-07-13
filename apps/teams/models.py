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

    max_players = models.PositiveSmallIntegerField(
        default=5,
    )

    is_active = models.BooleanField(
        default=True,
    )

    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="managed_teams",
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


class TeamMember(models.Model):
    """
    Represents a user's membership in a team.
    """

    class TeamRole(models.TextChoices):
        MANAGER = "MANAGER", "Manager"
        IGL = "IGL", "In-Game Leader"
        PLAYER = "PLAYER", "Player"

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="members",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="teams",
    )

    team_role = models.CharField(
    max_length=10,
    choices=TeamRole.choices,
    default=TeamRole.PLAYER,
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
        f"({self.team_role}) "
        f"- {self.team.name}"
    )

    
class TeamInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="invitations",
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_team_invitations",
    )

    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_team_invitations",
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.team.name} → "
            f"{self.receiver.username} "
            f"({self.status})"
        )

    