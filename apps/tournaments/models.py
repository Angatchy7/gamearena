from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Game(models.Model):
    """
    Supported games that tournaments can be created for.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    slug = models.SlugField(
        unique=True,
        blank=True,
    )

    logo = models.ImageField(
        upload_to="games/logos/",
        blank=True,
        null=True,
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tournament(models.Model):
    """
    Represents an esports tournament.
    """

    class TournamentType(models.TextChoices):
        SINGLE_ELIMINATION = (
            "SINGLE_ELIMINATION",
            "Single Elimination",
        )
        DOUBLE_ELIMINATION = (
            "DOUBLE_ELIMINATION",
            "Double Elimination",
        )
        ROUND_ROBIN = (
            "ROUND_ROBIN",
            "Round Robin",
        )
        SWISS = (
            "SWISS",
            "Swiss",
        )

    class ParticipationType(models.TextChoices):
        SOLO = "SOLO", "Solo"
        TEAM = "TEAM", "Team"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        REGISTRATION_OPEN = (
            "REGISTRATION_OPEN",
            "Registration Open",
        )
        REGISTRATION_CLOSED = (
            "REGISTRATION_CLOSED",
            "Registration Closed",
        )
        LIVE = "LIVE", "Live"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    class Visibility(models.TextChoices):
        PUBLIC = "PUBLIC", "Public"
        PRIVATE = "PRIVATE", "Private"
        INVITE_ONLY = "INVITE_ONLY", "Invite Only"

    name = models.CharField(
        max_length=150,
    )

    slug = models.SlugField(
        unique=True,
        blank=True,
    )

    game = models.ForeignKey(
        Game,
        on_delete=models.PROTECT,
        related_name="tournaments",
    )

    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organized_tournaments",
    )

    banner = models.ImageField(
        upload_to="tournaments/banners/",
        blank=True,
        null=True,
    )

    cover_image = models.ImageField(
        upload_to="tournaments/covers/",
        blank=True,
        null=True,
    )

    description = models.TextField()

    rules = models.TextField()

    tournament_type = models.CharField(
        max_length=30,
        choices=TournamentType.choices,
    )

    participation_type = models.CharField(
        max_length=10,
        choices=ParticipationType.choices,
        default=ParticipationType.TEAM,
    )

    team_size = models.PositiveSmallIntegerField(
        default=5,
    )

    max_participants = models.PositiveIntegerField()

    registration_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    prize_pool = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    registration_start = models.DateTimeField()

    registration_end = models.DateTimeField()

    start_date = models.DateTimeField()

    end_date = models.DateTimeField()

    contact_email = models.EmailField()

    discord_link = models.URLField(
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name