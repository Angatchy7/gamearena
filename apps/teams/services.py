from django.db import transaction

from .models import Team, TeamMember


@transaction.atomic
def create_team(*, manager, form):
    """
    Creates a new team and automatically
    adds the manager as the first member.
    """

    if Team.objects.filter(created_by=manager).exists():
        raise ValueError("You already own a team.")

    team = form.save(commit=False)
    team.created_by = manager
    team.save()

    TeamMember.objects.create(
        team=team,
        user=manager,
        management_role=TeamMember.ManagementRole.MANAGER,
        game_role=TeamMember.GameRole.PLAYER,
    )

    return team


@transaction.atomic
def update_team(*, team, form):
    """
    Updates an existing team.
    """

    team.name = form.cleaned_data["name"]
    team.description = form.cleaned_data["description"]
    team.max_players = form.cleaned_data["max_players"]

    # Only replace the logo if a new one was uploaded
    if form.cleaned_data.get("logo"):
        team.logo = form.cleaned_data["logo"]

    team.save()

    return team