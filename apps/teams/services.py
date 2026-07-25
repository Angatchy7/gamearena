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

    if Team.objects.filter(manager=manager).exists():
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

def accept_team_invitation(invitation):
    """
    Accept a pending invitation.
    """

    if invitation.status != TeamInvitation.Status.PENDING:
        return

    TeamMember.objects.create(
        team=invitation.team,
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