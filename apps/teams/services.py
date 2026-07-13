from django.db import transaction

from .models import Team, TeamMember


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