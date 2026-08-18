from django.conf import settings
from django.db import models
from django.utils.text import slugify
# pyrefly: ignore [missing-import]
from apps.teams.models import Team
from django.utils import timezone



import os

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
        max_length=255,
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
    def artwork_url(self):
        """Return the canonical public game artwork from local WebP assets.

        Uploaded logos remain available through image_url; public cards use this
        stable artwork so the homepage and tournament cards consistently render
        the same game-specific visual asset.
        """
        slug = (self.slug or "").lower()
        name = (self.name or "").lower()

        game_key = None
        if slug in ["pubg", "pubg-mobile", "battlegrounds-mobile-india"] or "pubg" in name or "battlegrounds" in name:
            game_key = "pubg"
        elif slug in ["valorant"] or "valorant" in name:
            game_key = "valorant"
        elif slug in ["rocket-league"] or "rocket league" in name or "rocket-league" in slug:
            game_key = "rocket_league"
        elif slug in ["free-fire", "garena-free-fire"] or "free fire" in name or "freefire" in name:
            game_key = "free_fire"
        elif slug in ["cs2", "counter-strike-2", "counter-strike"] or "counter-strike" in name or "cs2" in name:
            game_key = "cs2"
        elif slug in ["ea-sports-fc", "ea-fc", "fifa"] or "ea fc" in name or "ea sports fc" in name or "fifa" in name or "eafc" in slug:
            game_key = "eafc"
        elif slug in ["dota-2", "dota2", "dota"] or "dota" in name:
            game_key = "dota2"

        static_dir = os.path.join(settings.BASE_DIR, "static", "images", "games")
        if game_key:
            webp = os.path.join(static_dir, f"{game_key}.webp")
            if os.path.exists(webp):
                return f"/static/images/games/{game_key}.webp"

        default = os.path.join(settings.BASE_DIR, "static", "images", "defaults", "game_default.webp")
        if os.path.exists(default):
            return "/static/images/defaults/game_default.webp"
        return "/static/images/defaults/game_default.webp"

    @property
    def image_url(self):
        """Return an uploaded logo when available; otherwise use canonical WebP artwork."""
        if self.logo and self.logo.name:
            try:
                if self.logo.storage.exists(self.logo.name):
                    return self.logo.url
            except (AttributeError, ValueError):
                pass
        return self.artwork_url




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
        max_length=255,
        blank=True,
        null=True,
    )

    cover_image = models.ImageField(
        upload_to="tournaments/covers/",
        max_length=255,
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
        Returns the effective tournament status derived from datetime fields.
        Terminal states (DRAFT, CANCELLED, COMPLETED) are always respected.
        For published tournaments, state is computed from the current time:
          - Before registration window   → REGISTRATION_CLOSED (not yet open)
          - During registration window   → REGISTRATION_OPEN
          - After registration, before start → REGISTRATION_CLOSED
          - During tournament window     → LIVE
          - After end_date               → COMPLETED
        The DB field 'status' is the source-of-truth for DRAFT/CANCELLED/COMPLETED.
        """
        if self.status == self.Status.DRAFT:
            return self.Status.DRAFT

        if self.status == self.Status.CANCELLED:
            return self.Status.CANCELLED

        # If admin/service explicitly marked COMPLETED (e.g., champion set), keep it.
        if self.status == self.Status.COMPLETED:
            return self.Status.COMPLETED

        # Explicitly closed registration (e.g., organizer manually closed)
        if self.status == self.Status.REGISTRATION_CLOSED:
            return self.Status.REGISTRATION_CLOSED

        now = timezone.now()

        # Registration window has not started yet
        if now < self.registration_start:
            return self.Status.REGISTRATION_CLOSED

        # Within registration window
        if self.registration_start <= now <= self.registration_end:
            return self.Status.REGISTRATION_OPEN

        # Between registration close and tournament start
        if self.registration_end < now < self.start_date:
            return self.Status.REGISTRATION_CLOSED

        # Tournament is live
        if self.start_date <= now <= self.end_date:
            return self.Status.LIVE

        # Past end date
        return self.Status.COMPLETED

    @property
    def get_effective_status(self):
        """Alias for current_status for template compatibility."""
        return self.current_status

    @property
    def is_registration_open(self):
        """True only when registration is currently open."""
        return self.current_status == self.Status.REGISTRATION_OPEN

    @property
    def card_image_url(self):
        """Public tournament-card artwork: uploaded cover first, then game artwork."""
        if self.cover_image and self.cover_image.name:
            try:
                if self.cover_image.storage.exists(self.cover_image.name):
                    return self.cover_image.url
            except (AttributeError, ValueError):
                pass
        return self.game.artwork_url if self.game_id else "/static/images/defaults/tournament_cover.webp"

    @property
    def banner_display_url(self):
        """Public tournament hero art: uploaded banner/cover, then game artwork."""
        if self.banner and self.banner.name:
            try:
                if self.banner.storage.exists(self.banner.name):
                    return self.banner.url
            except (AttributeError, ValueError):
                pass
        if self.cover_image and self.cover_image.name:
            try:
                if self.cover_image.storage.exists(self.cover_image.name):
                    return self.cover_image.url
            except (AttributeError, ValueError):
                pass
        return self.game.artwork_url if self.game_id else "/static/images/defaults/tournament_banner.webp"

    @property
    def cover_url(self):
        """
        Priority: uploaded cover image -> uploaded banner -> game artwork -> default cover image.
        Falls back if the physical file no longer exists.
        """
        if self.cover_image and self.cover_image.name:
            try:
                if self.cover_image.storage.exists(self.cover_image.name):
                    return self.cover_image.url
            except (AttributeError, ValueError):
                pass
        if self.banner and self.banner.name:
            try:
                if self.banner.storage.exists(self.banner.name):
                    return self.banner.url
            except (AttributeError, ValueError):
                pass
        if self.game_id:
            return self.game.image_url

        default_dir = os.path.join(settings.BASE_DIR, "static", "images", "defaults")
        for ext in ["webp", "png", "jpg", "jpeg", "svg"]:
            if os.path.exists(os.path.join(default_dir, f"tournament_cover.{ext}")):
                return f"/static/images/defaults/tournament_cover.{ext}"

        return "/static/images/defaults/tournament_cover.webp"

    @property
    def banner_url(self):
        """
        Priority: uploaded banner -> uploaded cover image -> game artwork -> default banner image.
        Falls back if the physical file no longer exists.
        """
        if self.banner and self.banner.name:
            try:
                if self.banner.storage.exists(self.banner.name):
                    return self.banner.url
            except (AttributeError, ValueError):
                pass
        if self.cover_image and self.cover_image.name:
            try:
                if self.cover_image.storage.exists(self.cover_image.name):
                    return self.cover_image.url
            except (AttributeError, ValueError):
                pass
        if self.game_id:
            return self.game.image_url

        default_dir = os.path.join(settings.BASE_DIR, "static", "images", "defaults")
        for ext in ["webp", "png", "jpg", "jpeg", "svg"]:
            if os.path.exists(os.path.join(default_dir, f"tournament_banner.{ext}")):
                return f"/static/images/defaults/tournament_banner.{ext}"

        return "/static/images/defaults/tournament_banner.webp"

    @property
    def registered_count(self):
        """
        Returns the total number of registrations for this tournament.
        Uses annotated value if present, else counts database registrations.
        """
        if hasattr(self, "annotated_registered_count"):
            return self.annotated_registered_count
        return self.registrations.count()

    @property
    def champion_display(self):
        """
        Returns display_name of champion team/user.
        """
        if self.champion_id and self.champion:
            return self.champion.display_name
        return None





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
        if self.user_id and (not self.team_id or self.team.description == "__SOLO_INTERNAL__" or (self.team.name and self.team.name.startswith("__SOLO_"))):
            return self.user.username
        if self.team_id:
            return self.team.display_name
        if self.user_id:
            return self.user.username
        if self.registered_by_id:
            return self.registered_by.username
        return ""

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
        if self.team_one_id:
            return self.team_one.display_name
        return "BYE"

    @property
    def team_two_display(self):
        if self.team_two_id:
            return self.team_two.display_name
        return "BYE"

    @property
    def winner_display(self):
        if self.winner_id:
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
