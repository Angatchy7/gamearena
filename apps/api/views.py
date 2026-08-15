from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.teams.models import Team, TeamMember, TeamInvitation
from apps.tournaments.models import Game, Tournament, TournamentRegistration, Match, Round
from apps.notifications.models import Notification
from apps.notifications.services import (
    mark_notification_as_read,
    mark_all_notifications_as_read,
    get_unread_count,
)
from apps.tournaments.services import (
    register_solo_player,
    register_team,
    get_tournament_statistics,
    advance_winner,
)
from django.contrib.auth import get_user_model

from .permissions import IsTeamManager, IsTournamentOrganizer
from .serializers import (
    GameSerializer,
    GameDetailSerializer,
    TournamentListSerializer,
    TournamentDetailSerializer,
    TeamMemberSerializer,
    UserAutocompleteSerializer,
    TournamentRegistrationSerializer,
    MatchSerializer,
    NotificationSerializer,
    UserProfileSerializer,
)

User = get_user_model()


class GameListView(APIView):
    """
    GET /api/games/
    Returns collection of available Game records with tournament counts.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        games = Game.objects.filter(is_active=True).annotate(
            tournament_count=Count("tournaments")
        )
        serializer = GameSerializer(games, many=True)
        return Response(serializer.data)


class GameDetailView(APIView):
    """
    GET /api/games/<slug>/
    Returns single Game record.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        game = get_object_or_404(
            Game.objects.annotate(tournament_count=Count("tournaments")),
            slug=slug,
            is_active=True,
        )
        serializer = GameDetailSerializer(game)
        return Response(serializer.data)


class GameTournamentsView(APIView):
    """
    GET /api/games/<slug>/tournaments/
    Returns tournaments associated with a specific game.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        game = get_object_or_404(Game, slug=slug, is_active=True)
        queryset = Tournament.objects.filter(game=game).select_related("game", "organizer")

        status_param = request.GET.get("status", "").strip().lower()
        query_param = request.GET.get("q", "").strip()

        if query_param:
            queryset = queryset.filter(
                Q(name__icontains=query_param) | Q(description__icontains=query_param)
            )

        if status_param:
            filtered = []
            for t in queryset:
                eff_status = t.current_status.lower()
                if status_param == "upcoming" and eff_status in ["registration_open", "registration_closed"]:
                    filtered.append(t.pk)
                elif eff_status == status_param:
                    filtered.append(t.pk)
            queryset = queryset.filter(pk__in=filtered)

        serializer = TournamentListSerializer(queryset, many=True)
        return Response(serializer.data)


class TournamentListView(APIView):
    """
    GET /api/tournaments/
    Returns list of tournaments supporting game, status, and search filters.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        queryset = Tournament.objects.select_related("game", "organizer", "champion").prefetch_related("registrations")

        game_slug = request.GET.get("game", "").strip()
        status_param = request.GET.get("status", "").strip().lower()
        query_param = request.GET.get("q", "").strip()

        if game_slug:
            queryset = queryset.filter(game__slug=game_slug)

        if query_param:
            queryset = queryset.filter(
                Q(name__icontains=query_param) | Q(description__icontains=query_param)
            )

        if status_param:
            filtered = []
            for t in queryset:
                eff_status = t.current_status.lower()
                if status_param == "upcoming" and eff_status in ["registration_open", "registration_closed"]:
                    filtered.append(t.pk)
                elif eff_status == status_param:
                    filtered.append(t.pk)
            queryset = queryset.filter(pk__in=filtered)

        serializer = TournamentListSerializer(queryset, many=True)
        return Response(serializer.data)


class TournamentDetailView(APIView):
    """
    GET /api/tournaments/<id>/
    Returns single tournament details.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        tournament = get_object_or_404(
            Tournament.objects.select_related("game", "organizer", "champion"),
            pk=pk,
        )
        serializer = TournamentDetailSerializer(tournament)
        return Response(serializer.data)


class TeamMembersView(APIView):
    """
    GET /api/teams/<slug>/members/
    Returns active members of a team.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        team = get_object_or_404(Team, slug=slug)
        members = TeamMember.objects.filter(team=team, is_active=True).select_related("user")
        serializer = TeamMemberSerializer(members, many=True)
        return Response(serializer.data)


class UserAutocompleteAPIView(APIView):
    """
    GET /api/teams/<slug>/invite/search/?q=<username>
    Returns non-sensitive JSON user suggestions for team invitations.
    Requires authentication and manager authorization.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, slug):
        team = get_object_or_404(Team, slug=slug)

        if request.user != team.manager:
            return Response(
                {"detail": "Only the team manager can search players to invite."},
                status=status.HTTP_403_FORBIDDEN,
            )

        q = request.GET.get("q", "").strip()
        if not q:
            return Response([])

        member_user_ids = team.members.filter(is_active=True).values_list("user_id", flat=True)
        pending_invitee_ids = TeamInvitation.objects.filter(
            team=team, status=TeamInvitation.Status.PENDING
        ).values_list("receiver_id", flat=True)

        excluded_ids = set(member_user_ids) | set(pending_invitee_ids)
        excluded_ids.add(team.manager_id)

        users_qs = (
            User.objects.filter(username__icontains=q, is_active=True)
            .exclude(id__in=excluded_ids)
            .order_by("username")[:10]
        )

        serializer = UserAutocompleteSerializer(users_qs, many=True)
        return Response(serializer.data)


class TournamentRegistrationAPIView(APIView):
    """
    POST /api/tournaments/<id>/register/
    Registers the authenticated user for a SOLO or TEAM tournament.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        tournament = get_object_or_404(Tournament, pk=pk)

        if tournament.participation_type == Tournament.ParticipationType.SOLO:
            result = register_solo_player(tournament=tournament, user=request.user)
        else:
            team_id = request.data.get("team_id")
            team_slug = request.data.get("team_slug")
            if team_id:
                team = get_object_or_404(Team, pk=team_id)
            elif team_slug:
                team = get_object_or_404(Team, slug=team_slug)
            else:
                team = Team.objects.filter(manager=request.user, is_active=True).first()

            if not team:
                return Response(
                    {"detail": "You do not manage an active team for this registration."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            result = register_team(tournament=tournament, team=team, user=request.user)

        if result["success"]:
            serializer = TournamentRegistrationSerializer(result["registration"])
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {"detail": result["message"]},
                status=status.HTTP_400_BAD_REQUEST,
            )


class LeaderboardAPIView(APIView):
    """
    GET /api/tournaments/<id>/leaderboard/
    Returns tournament statistics and team/player rankings (safely formatted).
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        tournament = get_object_or_404(Tournament, pk=pk)
        stats = get_tournament_statistics(tournament=tournament)

        rankings_data = []
        for idx, r in enumerate(stats["team_rankings"], start=1):
            team_obj = r["team"]
            rankings_data.append({
                "rank": idx,
                "name": team_obj.display_name,
                "wins": r["wins"],
                "losses": r["losses"],
                "points": r["points"],
                "goals_scored": r["goals_scored"],
                "goals_conceded": r["goals_conceded"],
                "goal_difference": r["goal_difference"],
            })

        payload = {
            "tournament_id": tournament.id,
            "tournament_name": tournament.name,
            "total_matches": stats["total_matches_count"],
            "completed_matches": stats["completed_matches_count"],
            "completion_percentage": stats["completion_percentage"],
            "total_goals": stats["total_goals"],
            "avg_goals": stats["avg_goals"],
            "rankings": rankings_data,
        }

        return Response(payload)


class TournamentMatchesAPIView(APIView):
    """
    GET /api/tournaments/<id>/matches/
    Returns matches grouped by rounds for a tournament.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        tournament = get_object_or_404(Tournament, pk=pk)
        matches = Match.objects.filter(round__tournament=tournament).select_related(
            "round", "team_one", "team_two", "winner"
        ).order_by("round__order", "match_number")

        serializer = MatchSerializer(matches, many=True)
        return Response(serializer.data)


class MatchDetailAPIView(APIView):
    """
    GET /api/matches/<id>/
    Returns single match details.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        match_obj = get_object_or_404(
            Match.objects.select_related("round__tournament", "team_one", "team_two", "winner"),
            pk=pk,
        )
        serializer = MatchSerializer(match_obj)
        return Response(serializer.data)


class MatchResultAPIView(APIView):
    """
    POST /api/matches/<id>/result/
    Updates match score and advances winner. Requires tournament organizer permission.
    """

    permission_classes = [permissions.IsAuthenticated, IsTournamentOrganizer]

    def post(self, request, pk):
        match_obj = get_object_or_404(
            Match.objects.select_related("round__tournament", "team_one", "team_two"),
            pk=pk,
        )
        self.check_object_permissions(request, match_obj)

        try:
            team_one_score = int(request.data.get("team_one_score", 0))
            team_two_score = int(request.data.get("team_two_score", 0))
        except (ValueError, TypeError):
            return Response(
                {"detail": "Scores must be integer numbers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if team_one_score == team_two_score:
            return Response(
                {"detail": "Tie scores are not allowed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        match_obj.team_one_score = team_one_score
        match_obj.team_two_score = team_two_score
        match_obj.winner = match_obj.team_one if team_one_score > team_two_score else match_obj.team_two
        match_obj.status = Match.Status.COMPLETED
        match_obj.save()

        advance_winner(match=match_obj)

        serializer = MatchSerializer(match_obj)
        return Response(serializer.data, status=status.HTTP_200_OK)


class NotificationListView(APIView):
    """
    GET /api/notifications/
    Returns list of notifications for the authenticated user.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(recipient=request.user).order_by("-created_at")
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)


class NotificationUnreadView(APIView):
    """
    GET /api/notifications/unread/
    Returns unread count and unread notifications list for the authenticated user.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        unread_count = get_unread_count(user=request.user)
        unread_qs = Notification.objects.filter(recipient=request.user, is_read=False).order_by("-created_at")
        serializer = NotificationSerializer(unread_qs, many=True)
        return Response({
            "unread_count": unread_count,
            "results": serializer.data,
        })


class NotificationMarkReadView(APIView):
    """
    POST /api/notifications/<id>/read/
    Marks a single notification belonging to the authenticated user as read.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        mark_notification_as_read(notification=notification)
        serializer = NotificationSerializer(notification)
        return Response(serializer.data, status=status.HTTP_200_OK)


class NotificationMarkReadAllView(APIView):
    """
    POST /api/notifications/read-all/
    Marks all unread notifications for the authenticated user as read.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        updated_count = mark_all_notifications_as_read(user=request.user)
        return Response({
            "updated_count": updated_count,
            "detail": "All notifications marked as read.",
        }, status=status.HTTP_200_OK)


class UserProfileAPIView(APIView):
    """
    GET /api/profile/
    Returns safe account fields for the authenticated user.
    Strictly excludes sensitive fields (passwords, tokens, credentials).
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)


class DashboardAPIView(APIView):
    """
    GET /api/dashboard/
    Returns user dashboard summary using existing queries and display logic.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        user_team_qs = Team.objects.filter(
            Q(manager=user) | Q(members__user=user, members__is_active=True),
            is_active=True
        ).exclude(
            description="__SOLO_INTERNAL__"
        ).distinct().order_by("name")

        managed_teams_count = Team.objects.filter(manager=user, is_active=True).exclude(description="__SOLO_INTERNAL__").count()
        joined_teams_count = user_team_qs.count()

        organized_qs = Tournament.objects.filter(organizer=user)
        organized_count = organized_qs.count()
        active_organized_count = organized_qs.filter(
            status__in=[Tournament.Status.LIVE, Tournament.Status.REGISTRATION_OPEN]
        ).count()

        user_team_ids = [t.id for t in user_team_qs]
        joined_registrations = TournamentRegistration.objects.filter(
            Q(team_id__in=user_team_ids)
            | Q(user=user)
            | Q(registered_by=user, tournament__participation_type=Tournament.ParticipationType.SOLO)
        ).select_related("tournament", "tournament__game").distinct().order_by("-registered_at")

        joined_tournaments_count = len(set(reg.tournament_id for reg in joined_registrations))
        unread_notifications_count = get_unread_count(user=user)

        teams_data = [
            {
                "id": t.id,
                "name": t.display_name,
                "slug": t.slug,
                "logo_url": t.logo_url,
                "role": "MANAGER" if t.manager_id == user.id else "MEMBER",
            }
            for t in user_team_qs
        ]

        recent_notifications = Notification.objects.filter(recipient=user).order_by("-created_at")[:5]
        notification_serializer = NotificationSerializer(recent_notifications, many=True)

        payload = {
            "user": {
                "id": user.id,
                "username": user.username,
                "role": getattr(user, "role", "USER"),
            },
            "metrics": {
                "managed_teams_count": managed_teams_count,
                "joined_teams_count": joined_teams_count,
                "organized_tournaments_count": organized_count,
                "active_organized_count": active_organized_count,
                "joined_tournaments_count": joined_tournaments_count,
                "unread_notifications_count": unread_notifications_count,
            },
            "teams": teams_data,
            "recent_notifications": notification_serializer.data,
        }

        return Response(payload)


class TournamentStatisticsAPIView(APIView):
    """
    GET /api/tournaments/<id>/statistics/
    Returns tournament statistics reusing get_tournament_statistics service.
    Formatting uses display_name (real team names for TEAM, real usernames for SOLO, zero __SOLO_ leakage).
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        tournament = get_object_or_404(Tournament, pk=pk)
        stats = get_tournament_statistics(tournament=tournament)

        rankings_data = []
        for idx, r in enumerate(stats["team_rankings"], start=1):
            team_obj = r["team"]
            rankings_data.append({
                "rank": idx,
                "name": team_obj.display_name,
                "wins": r["wins"],
                "losses": r["losses"],
                "points": r["points"],
                "goals_scored": r["goals_scored"],
                "goals_conceded": r["goals_conceded"],
                "goal_difference": r["goal_difference"],
                "win_rate": r.get("win_rate", 0.0),
            })

        payload = {
            "tournament_id": tournament.id,
            "tournament_name": tournament.name,
            "participation_type": tournament.participation_type,
            "participant_count": stats["participant_count"],
            "registration_percentage": stats["registration_percentage"],
            "total_matches": stats["total_matches_count"],
            "completed_matches": stats["completed_matches_count"],
            "remaining_matches": stats["remaining_matches_count"],
            "completion_percentage": stats["completion_percentage"],
            "total_goals": stats["total_goals"],
            "avg_goals": stats["avg_goals"],
            "rankings": rankings_data,
        }

        return Response(payload)

