from django.conf import settings
from django.db import models
# pyrefly: ignore [missing-import]
from apps.teams.models import TeamInvitation


class Notification(models.Model):

    class Type(models.TextChoices):
        TEAM_INVITATION = "TEAM_INVITATION", "Team Invitation"
        TOURNAMENT_INVITATION = "TOURNAMENT_INVITATION", "Tournament Invitation"
        TOURNAMENT = "TOURNAMENT", "Tournament"
        MATCH = "MATCH", "Match"
        SYSTEM = "SYSTEM", "System"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    team_invitation = models.ForeignKey(
        TeamInvitation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    title = models.CharField(
        max_length=150,
    )

    message = models.TextField()

    notification_type = models.CharField(
        max_length=30,
        choices=Type.choices,
        default=Type.SYSTEM,
    )

    is_read = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title