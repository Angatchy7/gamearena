from django.conf import settings
from django.db import models
from django.utils.text import slugify
# pyrefly: ignore [missing-import]
from apps.teams.models import Team
from django.utils import timezone



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

    @property
    def image_url(self):
        """
        Returns uploaded game logo URL if present, else specific game artwork, else generic game default.
        """
        if self.logo:
            try:
                return self.logo.url
            except (AttributeError, ValueError):
                if getattr(self.logo, "name", None):
                    url_str = str(self.logo.name)
                    if not url_str.startswith("/") and not url_str.startswith("http"):
                        return f"{settings.MEDIA_URL}{url_str}"
                    return url_str

        slug = (self.slug or "").lower()
        name = (self.name or "").lower()


        if "pubg" in slug or "pubg" in name:
            return f"{settings.STATIC_URL}images/games/pubg.svg"
        if "valorant" in slug or "valorant" in name:
            return f"{settings.STATIC_URL}images/games/valorant.svg"
        if "ea" in slug or "fc" in slug or "fifa" in slug or "ea" in name or "fc" in name or "fifa" in name:
            return f"{settings.STATIC_URL}images/games/eafc.svg"
        if "rocket" in slug or "league" in slug or "rocket" in name:
            return f"{settings.STATIC_URL}images/games/rocket_league.svg"
        if "cs2" in slug or "cs2" in name or "counter-strike" in slug or "counter-strike" in name:
            return f"{settings.STATIC_URL}images/games/cs2.svg"

        return f"{settings.STATIC_URL}images/defaults/game_default.svg"




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

    champion = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="championships_won",
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
        if self.participation_type == self.ParticipationType.SOLO:
            self.team_size = 1

        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Tournament.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        super().save(*args, **kwargs)

    @property
    def current_status(self):
        """
        Returns the current tournament status based on
        dates while respecting Draft and Cancelled.
        """

        if self.status == self.Status.DRAFT:
            return self.Status.DRAFT

        if self.status == self.Status.CANCELLED:
            return self.Status.CANCELLED

        now = timezone.now()

        if now < self.registration_start:
            return self.Status.REGISTRATION_OPEN

        if self.registration_start <= now <= self.registration_end:
            return self.Status.REGISTRATION_OPEN

        if self.registration_end < now < self.start_date:
            return self.Status.REGISTRATION_CLOSED

        if self.start_date <= now <= self.end_date:
            return self.Status.LIVE

        return self.Status.COMPLETED

    @property
    def cover_url(self):
        """
        Priority: uploaded cover image -> uploaded banner -> game artwork -> default cover SVG.
        """
        if self.cover_image:
            try:
                return self.cover_image.url
            except (AttributeError, ValueError):
                if getattr(self.cover_image, "name", None):
                    url_str = str(self.cover_image.name)
                    if not url_str.startswith("/") and not url_str.startswith("http"):
                        return f"{settings.MEDIA_URL}{url_str}"
                    return url_str
        if self.banner:
            try:
                return self.banner.url
            except (AttributeError, ValueError):
                if getattr(self.banner, "name", None):
                    url_str = str(self.banner.name)
                    if not url_str.startswith("/") and not url_str.startswith("http"):
                        return f"{settings.MEDIA_URL}{url_str}"
                    return url_str
        if self.game:
            return self.game.image_url
        return f"{settings.STATIC_URL}images/defaults/tournament_cover.svg"

    @property
    def banner_url(self):
        """
        Priority: uploaded banner -> uploaded cover image -> game artwork -> default banner SVG.
        """
        if self.banner:
            try:
                return self.banner.url
            except (AttributeError, ValueError):
                if getattr(self.banner, "name", None):
                    url_str = str(self.banner.name)
                    if not url_str.startswith("/") and not url_str.startswith("http"):
                        return f"{settings.MEDIA_URL}{url_str}"
                    return url_str
        if self.cover_image:
            try:
                return self.cover_image.url
            except (AttributeError, ValueError):
                if getattr(self.cover_image, "name", None):
                    url_str = str(self.cover_image.name)
                    if not url_str.startswith("/") and not url_str.startswith("http"):
                        return f"{settings.MEDIA_URL}{url_str}"
                    return url_str
        if self.game:
            return self.game.image_url
        return f"{settings.STATIC_URL}images/defaults/tournament_banner.svg"




class TournamentRegistration(models.Model):
    """
    A team or individual player's registration in a tournament.
    """

    class Status(models.TextChoices):
        REGISTERED = "REGISTERED", "Registered"
        CHECKED_IN = "CHECKED_IN", "Checked In"
        ELIMINATED = "ELIMINATED", "Eliminated"
        DISQUALIFIED = "DISQUALIFIED", "Disqualified"

    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name="registrations",
    )

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="tournament_registrations",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="solo_tournament_registrations",
    )

    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REGISTERED,
    )

    registered_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["registered_at"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "tournament",
                    "team",
                ],
                condition=models.Q(team__isnull=False),
                name="unique_team_registration",
            ),
            models.UniqueConstraint(
                fields=[
                    "tournament",
                    "user",
                ],
                condition=models.Q(user__isnull=False),
                name="unique_user_solo_registration",
            ),
        ]

    @property
    def display_name(self):
        """
        Returns player's username for SOLO registration and team's display_name for TEAM registration.
        """
        if self.user and (not self.team or self.team.description == "__SOLO_INTERNAL__" or (self.team.name and self.team.name.startswith("__SOLO_"))):
            return self.user.username
        if self.team:
            return self.team.display_name
        if self.user:
            return self.user.username
        return self.registered_by.username

    def get_notification_users(self):
        """
        Returns User instances associated with this registration for notifications.
        """
        from apps.teams.models import TeamMember
        users = set()
        if self.user:
            users.add(self.user)
        elif self.team:
            if self.team.description == "__SOLO_INTERNAL__" or (self.team.name and self.team.name.startswith("__SOLO_")):
                if self.team.manager:
                    users.add(self.team.manager)
            else:
                active_members = TeamMember.objects.filter(team=self.team, is_active=True).select_related("user")
                for member in active_members:
                    users.add(member.user)
        if self.registered_by:
            users.add(self.registered_by)
        return list(users)

    def get_notification_emails(self):
        """
        Returns email addresses for notification delivery.
        """
        return [user.email for user in self.get_notification_users() if user.email]

    def __str__(self):
        return f"{self.display_name} - {self.tournament.name}"


class Round(models.Model):
    """
    Represents one round of a tournament.
    """

    tournament = models.ForeignKey(
    Tournament,
    on_delete=models.CASCADE,
    related_name="rounds",
    )

    name = models.CharField(
        max_length=50,
    )

    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["order"]
        unique_together = (
            "tournament",
            "order",
        )

    def __str__(self):
        return f"{self.tournament.name} - {self.name}"

class Match(models.Model):
    """
    Represents a single match.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        LIVE = "LIVE", "Live"
        COMPLETED = "COMPLETED", "Completed"

    round = models.ForeignKey(
    Round,
    on_delete=models.CASCADE,
    related_name="matches",
    )

    match_number = models.PositiveIntegerField()

    team_one = models.ForeignKey(
        "teams.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="team_one_matches",
    )

    team_two = models.ForeignKey(
        "teams.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="team_two_matches",
    )

    winner = models.ForeignKey(
        "teams.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="won_matches",
    )

    team_one_score = models.PositiveSmallIntegerField(
        default=0,
    )

    team_two_score = models.PositiveSmallIntegerField(
        default=0,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    class Meta:
        ordering = [
            "round",
            "match_number",
        ]

    @property
    def team_one_display(self):
        if self.team_one:
            return self.team_one.display_name
        return "BYE"

    @property
    def team_two_display(self):
        if self.team_two:
            return self.team_two.display_name
        return "BYE"

    @property
    def winner_display(self):
        if self.winner:
            return self.winner.display_name
        return None

    def get_participant_users(self):
        """
        Returns a list of User instances participating in this match.
        """
        from apps.teams.models import TeamMember
        users = set()
        for team in [self.team_one, self.team_two]:
            if not team:
                continue
            if team.description == "__SOLO_INTERNAL__" or (team.name and team.name.startswith("__SOLO_")):
                if team.manager:
                    users.add(team.manager)
            else:
                active_members = TeamMember.objects.filter(team=team, is_active=True).select_related("user")
                for member in active_members:
                    users.add(member.user)
        return list(users)

    def get_participant_emails(self):
        """
        Returns email addresses for match notification delivery.
        """
        return [user.email for user in self.get_participant_users() if user.email]

    def __str__(self):
        return (
            f"{self.round.name} - Match {self.match_number}"
        )