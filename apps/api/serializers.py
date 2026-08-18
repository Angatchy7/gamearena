from rest_framework import serializers
from apps.tournaments.models import Game, Tournament, TournamentRegistration, Match
from apps.teams.models import Team, TeamMember
from apps.notifications.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for Notification instances. Exposes safe notification details.
    """

    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "message",
            "notification_type",
            "is_read",
            "created_at",
        ]


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for User profile endpoint. Exposes only safe account information.
    Strictly excludes sensitive fields (password, tokens, etc).
    """

    class Meta:
        model = User
        fields = ["id", "username", "email", "role"]


class UserAutocompleteSerializer(serializers.ModelSerializer):
    """
    Serializer for user autocomplete in team invitations. Exposes only safe fields.
    """

    class Meta:
        model = User
        fields = ["id", "username"]


class TeamMemberSerializer(serializers.ModelSerializer):
    """
    Serializer for active team members.
    """

    id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = TeamMember
        fields = ["id", "username", "team_role", "joined_at"]


class GameSerializer(serializers.ModelSerializer):
    """
    Serializer for Game catalog.
    """

    image_url = serializers.CharField(read_only=True)
    tournament_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Game
        fields = ["id", "name", "slug", "image_url", "tournament_count"]


class GameDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for single Game.
    """

    image_url = serializers.CharField(read_only=True)
    tournament_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Game
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "image_url",
            "tournament_count",
            "is_active",
            "created_at",
        ]


class GameSimpleSerializer(serializers.ModelSerializer):
    """
    Simple nested Game serializer for Tournaments and Teams.
    """

    image_url = serializers.CharField(read_only=True)

    class Meta:
        model = Game
        fields = ["id", "name", "slug", "image_url"]


class TeamSerializer(serializers.ModelSerializer):
    """
    Serializer for listing and summary of teams.
    """

    game = GameSimpleSerializer(read_only=True)
    manager = serializers.CharField(source="manager.username", read_only=True)
    display_name = serializers.CharField(read_only=True)
    logo_url = serializers.CharField(read_only=True)
    active_member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Team
        fields = [
            "id",
            "name",
            "display_name",
            "slug",
            "description",
            "logo_url",
            "max_players",
            "is_active",
            "game",
            "manager",
            "active_member_count",
            "created_at",
        ]


class TeamAPIDetailSerializer(serializers.ModelSerializer):
    """
    Detailed Team serializer including roster.
    """

    game = GameSimpleSerializer(read_only=True)
    manager = serializers.CharField(source="manager.username", read_only=True)
    display_name = serializers.CharField(read_only=True)
    logo_url = serializers.CharField(read_only=True)
    active_member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Team
        fields = [
            "id",
            "name",
            "display_name",
            "slug",
            "description",
            "logo_url",
            "max_players",
            "is_active",
            "game",
            "manager",
            "active_member_count",
            "created_at",
        ]


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)


class ResetPasswordAPISerializer(serializers.Serializer):
    reset_token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs


class ChangePasswordVerifySerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs



class TournamentListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing Tournaments.
    """

    game = GameSimpleSerializer(read_only=True)
    organizer = serializers.CharField(source="organizer.username", read_only=True)
    status = serializers.CharField(source="current_status", read_only=True)
    registration_status = serializers.CharField(source="current_status", read_only=True)
    cover_url = serializers.CharField(read_only=True)
    banner_url = serializers.CharField(read_only=True)
    participant_count = serializers.SerializerMethodField()

    class Meta:
        model = Tournament
        fields = [
            "id",
            "name",
            "slug",
            "game",
            "organizer",
            "status",
            "registration_status",
            "registration_start",
            "registration_end",
            "start_date",
            "end_date",
            "registration_fee",
            "prize_pool",
            "cover_url",
            "banner_url",
            "participation_type",
            "team_size",
            "max_participants",
            "participant_count",
        ]

    def get_participant_count(self, obj):
        return obj.registrations.count()


class TournamentDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for a single Tournament.
    """

    game = GameSimpleSerializer(read_only=True)
    organizer = serializers.CharField(source="organizer.username", read_only=True)
    status = serializers.CharField(source="current_status", read_only=True)
    registration_status = serializers.CharField(source="current_status", read_only=True)
    cover_url = serializers.CharField(read_only=True)
    banner_url = serializers.CharField(read_only=True)
    participant_count = serializers.SerializerMethodField()
    champion_name = serializers.SerializerMethodField()

    class Meta:
        model = Tournament
        fields = [
            "id",
            "name",
            "slug",
            "game",
            "organizer",
            "description",
            "rules",
            "tournament_type",
            "participation_type",
            "team_size",
            "max_participants",
            "participant_count",
            "registration_fee",
            "prize_pool",
            "registration_start",
            "registration_end",
            "start_date",
            "end_date",
            "contact_email",
            "discord_link",
            "status",
            "registration_status",
            "visibility",
            "champion_name",
            "cover_url",
            "banner_url",
            "created_at",
        ]

    def get_participant_count(self, obj):
        return obj.registrations.count()

    def get_champion_name(self, obj):
        if obj.champion_id:
            return obj.champion.display_name
        return None


class TournamentRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for Tournament Registration results.
    """

    tournament_name = serializers.CharField(source="tournament.name", read_only=True)
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = TournamentRegistration
        fields = [
            "id",
            "tournament",
            "tournament_name",
            "display_name",
            "status",
            "registered_at",
        ]


class MatchSerializer(serializers.ModelSerializer):
    """
    Serializer for Match records.
    """

    round_name = serializers.CharField(source="round.name", read_only=True)
    round_order = serializers.IntegerField(source="round.order", read_only=True)
    team_one_display = serializers.CharField(read_only=True)
    team_two_display = serializers.CharField(read_only=True)
    winner_display = serializers.CharField(read_only=True)

    class Meta:
        model = Match
        fields = [
            "id",
            "match_number",
            "round_name",
            "round_order",
            "team_one_display",
            "team_two_display",
            "team_one_score",
            "team_two_score",
            "winner_display",
            "status",
        ]
