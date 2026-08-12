from django.db import transaction

from .models import Team, TeamMember, TeamInvitation

# pyrefly: ignore [missing-import]
from apps.notifications.models import Notification

@transaction.atomic
def create_team(*, manager, form):
    """
    Creates a new team and automatically
    adds the manager as the first member.
    """

    if Team.objects.filter(manager=manager).exclude(description="__SOLO_INTERNAL__").exists():
        return {
            "success": False,
            "message": "You already manage a team.",
        }

    team = form.save(commit=False)
    team.manager = manager
    team.save()

    TeamMember.objects.create(
        team=team,
        user=manager,
        team_role=TeamMember.TeamRole.MANAGER,
    )

    return {
        "success": True,
        "message": "Team created successfully.",
        "team": team,
    }


@transaction.atomic
def update_team(*, team, form):
    """
    Updates an existing team.
    """

    team.name = form.cleaned_data["name"]
    team.description = form.cleaned_data["description"]
    team.max_players = form.cleaned_data["max_players"]

    if form.cleaned_data.get("logo"):
        team.logo = form.cleaned_data["logo"]

    team.save()

    return {
        "success": True,
        "message": "Team updated successfully.",
        "team": team,
    }

def send_team_invitation(team,sender,receiver,):
    """
    Sends a team invitation.
    """

    if sender != team.manager:
        return {
            "success": False,
            "message": "Only the team manager can invite players.",
        }

    active_members = TeamMember.objects.filter(
        team=team,
        is_active=True,
    ).count()

    if active_members >= team.max_players:
        return {
            "success": False,
            "message": "Team has reached maximum player capacity.",
        }

    if TeamMember.objects.filter(
        team=team,
        user=receiver,
        is_active=True,
    ).exists():
        return {
            "success": False,
            "message": "User is already a team member.",
        }

    if TeamInvitation.objects.filter(
        team=team,
        receiver=receiver,
        status=TeamInvitation.Status.PENDING,
    ).exists():
        return {
            "success": False,
            "message": "A pending invitation already exists.",
        }

    invitation = TeamInvitation.objects.create(
        team=team,
        sender=sender,
        receiver=receiver,
    )

    Notification.objects.create(
        recipient=receiver,
        title="Team Invitation",
        message=(
            f"{sender.username} invited you to join "
            f"'{team.name}'."
        ),
    notification_type=Notification.Type.TEAM_INVITATION,
    team_invitation=invitation,
    )

    return {
        "success": True,
        "invitation": invitation,
    }

@transaction.atomic
def accept_team_invitation(invitation):
    """
    Accept a pending invitation.
    """

    if invitation.status != TeamInvitation.Status.PENDING:
        return {
            "success": False,
            "message": "Invitation is no longer pending.",
        }

    team = invitation.team

    active_members = TeamMember.objects.filter(
        team=team,
        is_active=True,
    ).count()

    if active_members >= team.max_players:
        return {
            "success": False,
            "message": "Team has reached maximum player capacity.",
        }

    TeamMember.objects.create(
        team=team,
        user=invitation.receiver,
        team_role=TeamMember.TeamRole.PLAYER,
    )

    invitation.status = TeamInvitation.Status.ACCEPTED
    invitation.save()

    Notification.objects.filter(
        team_invitation=invitation,
    ).update(
        is_read=True,
    )

    return {
        "success": True,
        "message": "Invitation accepted successfully.",
    }


def reject_team_invitation(invitation):
    """
    Reject a pending invitation.
    """

    if invitation.status != TeamInvitation.Status.PENDING:
        return

    invitation.status = TeamInvitation.Status.REJECTED
    invitation.save()

    Notification.objects.filter(
        team_invitation=invitation,
    ).update(
        is_read=True,
    )


from django.db.models import Q
from apps.tournaments.models import TournamentRegistration, Match, Tournament


def get_team_profile_data(*, team):
    """
    Computes complete profile statistics, roster, tournaments, and recent matches for a team.
    """

    members = (
        TeamMember.objects.filter(
            team=team,
            is_active=True,
        )
        .select_related("user")
        .order_by("joined_at")
    )

    captain = team.manager

    registrations = (
        TournamentRegistration.objects.filter(
            team=team,
        )
        .select_related("tournament", "tournament__game")
        .order_by("-registered_at")
    )

    active_tournaments = [
        reg.tournament
        for reg in registrations
        if reg.tournament.status
        in [
            Tournament.Status.REGISTRATION_OPEN,
            Tournament.Status.REGISTRATION_CLOSED,
            Tournament.Status.LIVE,
            Tournament.Status.DRAFT,
        ]
    ]

    tournament_history = [
        reg.tournament
        for reg in registrations
        if reg.tournament.status == Tournament.Status.COMPLETED
    ]

    all_team_matches = list(
        Match.objects.filter(Q(team_one=team) | Q(team_two=team))
        .select_related("round__tournament", "team_one", "team_two", "winner")
        .order_by("-id")
    )

    completed_matches = [
        m for m in all_team_matches if m.status == Match.Status.COMPLETED and m.team_one and m.team_two
    ]

    wins = sum(1 for m in completed_matches if m.winner == team)
    losses = sum(1 for m in completed_matches if m.winner and m.winner != team)
    matches_played = len(completed_matches)

    win_rate = (
        round((wins / matches_played) * 100, 1)
        if matches_played > 0
        else 0.0
    )

    processed_recent_matches = []
    for match in all_team_matches[:10]:
        is_team_one = match.team_one == team
        opponent = match.team_two if is_team_one else match.team_one
        team_score = (
            match.team_one_score if is_team_one else match.team_two_score
        )
        opponent_score = (
            match.team_two_score if is_team_one else match.team_one_score
        )
        is_winner = (match.winner == team) if match.winner else False

        processed_recent_matches.append(
            {
                "match": match,
                "tournament": match.round.tournament,
                "round": match.round,
                "opponent": opponent,
                "team_score": team_score,
                "opponent_score": opponent_score,
                "is_winner": is_winner,
                "is_completed": (match.status == Match.Status.COMPLETED),
            }
        )

    return {
        "team": team,
        "captain": captain,
        "members": members,
        "active_tournaments": active_tournaments,
        "tournament_history": tournament_history,
        "wins": wins,
        "losses": losses,
        "matches_played": matches_played,
        "win_rate": win_rate,
        "recent_matches": processed_recent_matches,
    }