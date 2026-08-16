from django import forms
from django.contrib.auth import get_user_model

from .models import Team, TeamInvitation
from apps.tournaments.models import Game

User = get_user_model()


class TeamCreateForm(forms.ModelForm):
    """
    Form for creating a team. Requires selecting a game.
    """
    game = forms.ModelChoiceField(
        queryset=Game.objects.filter(is_active=True),
        required=True,
        empty_label="Select a game",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Team

        fields = [
            "name",
            "game",
            "description",
            "logo",
            "max_players",
        ]


class TeamUpdateForm(forms.ModelForm):
    """
    Form for updating a team.
    """

    class Meta:
        model = Team

        fields = [
            "name",
            "description",
            "logo",
            "max_players",
            "is_active",
        ]


class TeamInvitationForm(forms.ModelForm):
    """
    Form for inviting a player to a team.
    """

    receiver = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label="Player",
        empty_label="Select a player",
    )

    class Meta:
        model = TeamInvitation

        fields = [
            "receiver",
        ]

    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)

        if team:

            # Users already in the team
            member_ids = team.members.values_list(
                "user_id",
                flat=True,
            )

            # Exclude manager and existing members
            self.fields["receiver"].queryset = (
                User.objects.exclude(
                    id__in=member_ids,
                ).exclude(
                    id=team.manager_id,
                )
            )