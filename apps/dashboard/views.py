from django.contrib.auth.decorators import login_required
from django.shortcuts import render

# pyrefly: ignore [missing-import]

from apps.core.decorators import admin_required

# pyrefly: ignore [missing-import]

from apps.tournaments.models import Tournament, TournamentRegistration

# pyrefly: ignore [missing-import]

from apps.teams.models import Team, TeamMember

# pyrefly: ignore [missing-import]

from apps.notifications.models import Notification

from django.db.models import Count, Q


@login_required
def dashboard_home(request):
    """
    Main dashboard for all users.
    """
    user = request.user

    # User's teams annotated with active member count
    managed_teams = Team.objects.filter(manager=user, is_active=True).annotate(
        _active_member_count=Count("members", filter=Q(members__is_active=True), distinct=True)
    )
    user_team_qs = Team.objects.filter(
        Q(manager=user) | Q(members__user=user, members__is_active=True),
        is_active=True
    ).distinct().annotate(
        _active_member_count=Count("members", filter=Q(members__is_active=True), distinct=True)
    ).order_by("name")
    user_teams = list(user_team_qs)

    # User's organized tournaments
    organized_tournaments = Tournament.objects.filter(organizer=user).select_related("game").order_by("-created_at")

    # Tournaments joined by user's teams
    user_team_ids = [t.id for t in user_teams]
    joined_registrations = (
        TournamentRegistration.objects
        .filter(team_id__in=user_team_ids)
        .select_related("tournament", "tournament__game", "team")
        .order_by("-registered_at")
    )

    joined_tournaments = [reg.tournament for reg in joined_registrations]

    # Recent notifications / activity
    recent_notifications = Notification.objects.filter(recipient=user).order_by("-created_at")[:6]
    unread_notifications_count = Notification.objects.filter(recipient=user, is_read=False).count()

    total_organized = organized_tournaments.count()
    active_organized = organized_tournaments.filter(
        status__in=[Tournament.Status.LIVE, Tournament.Status.REGISTRATION_OPEN]
    ).count()

    context = {
        "user_teams": user_teams,
        "managed_teams": managed_teams,
        "organized_tournaments": organized_tournaments[:4],
        "all_organized_count": total_organized,
        "active_organized_count": active_organized,
        "joined_registrations": joined_registrations[:5],
        "joined_tournaments_count": len(joined_tournaments),
        "recent_notifications": recent_notifications,
        "unread_notifications_count": unread_notifications_count,
    }
    return render(request, "dashboard/home.html", context)


@login_required
@admin_required
def admin_dashboard(request):
    """
    Website administrator dashboard.
    """
    return render(request, "dashboard/admin.html")  