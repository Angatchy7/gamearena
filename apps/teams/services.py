from django.db import transaction

from .models import Team, TeamMembership


@transaction.atomic
def create_team(*, captain, form):

    if Team.objects.filter(created_by=captain).exists():
        raise ValueError("You already own a team.")

    team = form.save(commit=False)
    team.created_by = captain
    team.save()

    TeamMembership.objects.create(
        team=team,
        user=captain,
        management_role=TeamMembership.ManagementRole.CAPTAIN,
        game_role=TeamMembership.GameRole.PLAYER,
    )

    return team