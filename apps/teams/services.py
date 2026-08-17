from django.db import transaction

from .models import Team, TeamMember, TeamInvitation

# pyrefly: ignore [missing-import]
from apps.notifications.models import Notification

@transaction.atomic
def create_team(*, manager, form=None, name=None, game=None, description="", logo=None, max_players=5):
    """
    Creates a new team and automatically adds the manager as the first member.
    Enforces one active team per game per manager.
    Can be invoked with a Django form or raw keyword args.
    """
    if form is not None:
        team = form.save(commit=False)
        team.manager = manager
        if not team.game_id and form.cleaned_data.get("game"):
            team.game = form.cleaned_data["game"]
    else:
        if not name:
            return {
                "success": False,
                "message": "Team name is required.",
            }
        team = Team(
            name=name,
            game=game,
            description=description or "",
            logo=logo,
            max_players=max_players or 5,
            manager=manager,
        )

    if not team.game_id:
        return {
            "success": False,
            "message": "Game selection is required for team creation.",
        }

    if Team.objects.filter(manager=manager, game=team.game, is_active=True).exclude(description="__SOLO_INTERNAL__").exists():
        return {
            "success": False,
            "message": f"You already manage a team for {team.game.name}.",
        }

    team.save()

    TeamMember.objects.get_or_create(
        team=team,
        user=manager,
        defaults={
            "team_role": TeamMember.TeamRole.MANAGER,
            "is_active": True,
        },
    )

    return {
        "success": True,
        "message": "Team created successfully.",
        "team": team,
    }


@transaction.atomic
def update_team(*, team, form=None, name=None, description=None, logo=None, max_players=None, is_active=None):
    """
    Updates an existing team. Accepts either a Django form or keyword arguments.
    """
    if form is not None:
        team.name = form.cleaned_data["name"]
        team.description = form.cleaned_data["description"]
        team.max_players = form.cleaned_data["max_players"]
        if "game" in form.cleaned_data and form.cleaned_data["game"]:
            team.game = form.cleaned_data["game"]
        if form.cleaned_data.get("logo"):
            team.logo = form.cleaned_data["logo"]
        if "is_active" in form.cleaned_data:
            team.is_active = form.cleaned_data["is_active"]
    else:
        if name is not None:
            team.name = name
        if description is not None:
            team.description = description
        if max_players is not None:
            team.max_players = max_players
        if logo is not None:
            team.logo = logo
        if is_active is not None:
            team.is_active = is_active

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


@transaction.atomic
def remove_team_member(*, team, manager, member_user):
    """
    Soft-removes a player from a team by deactivating their TeamMember record.
    Only the team manager can perform this action.
    The manager cannot remove themselves.
    Returns a dict with 'success' and 'message'.
    """
    from django.utils import timezone as tz

    if manager != team.manager:
        return {
            "success": False,
            "message": "Only the team manager can remove players.",
        }

    if member_user == team.manager:
        return {
            "success": False,
            "message": "The manager cannot remove themselves from the team.",
        }

    try:
        membership = TeamMember.objects.get(
            team=team,
            user=member_user,
            is_active=True,
        )
    except TeamMember.DoesNotExist:
        return {
            "success": False,
            "message": "This user is not an active member of the team.",
        }

    membership.is_active = False
    membership.left_at = tz.now()
    membership.save(update_fields=["is_active", "left_at"])

    return {
        "success": True,
        "message": f"{member_user.username} has been removed from the team.",
    }


@transaction.atomic
def delete_team(*, team, user):
    """
    Deactivates a team and all active team memberships, recording left_at timestamp.
    Preserves historical tournament registrations, matches, statistics, and notifications.
    Only team manager or authorized admin can perform this operation.
    """
    from django.utils import timezone as tz

    is_admin = getattr(user, "is_staff", False) or getattr(user, "role", "") == "ADMIN"
    if user != team.manager and not is_admin:
        return {
            "success": False,
            "message": "Only the team manager or authorized admin can delete this team.",
        }

    now = tz.now()
    team.is_active = False
    team.save(update_fields=["is_active"])

    # Deactivate active team members and set left_at
    TeamMember.objects.filter(team=team, is_active=True).update(
        is_active=False,
        left_at=now,
    )

    return {
        "success": True,
        "message": f"Team '{team.name}' has been deactivated successfully.",
    }


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