from datetime import timezone
from django import forms
# pyrefly: ignore [missing-import]
from apps.teams.models import Team
from .models import Match, Tournament, TournamentRegistration


class TournamentCreateForm(forms.ModelForm):

    class Meta:
        model = Tournament

        fields = (
            "name",
            "game",
            "banner",
            "cover_image",
            "description",
            "rules",
            "tournament_type",
            "participation_type",
            "team_size",
            "max_participants",
            "registration_fee",
            "prize_pool",
            "registration_start",
            "registration_end",
            "start_date",
            "end_date",
            "contact_email",
            "discord_link",
            "visibility",
        )

        widgets = {

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Tournament Name",
                }
            ),

            "game": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "banner": forms.FileInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "cover_image": forms.FileInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),

            "rules": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                }
            ),

            "tournament_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "participation_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "team_size": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                }
            ),

            "max_participants": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 2,
                }
            ),

            "registration_fee": forms.NumberInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "prize_pool": forms.NumberInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "registration_start": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
            ),

            "registration_end": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
            ),

            "start_date": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
            ),

            "end_date": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
            ),

            "contact_email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "discord_link": forms.URLInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "visibility": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }

    input_formats = {
        "registration_start": ["%Y-%m-%dT%H:%M"],
        "registration_end": ["%Y-%m-%dT%H:%M"],
        "start_date": ["%Y-%m-%dT%H:%M"],
        "end_date": ["%Y-%m-%dT%H:%M"],
    }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        for field, formats in self.input_formats.items():
            self.fields[field].input_formats = formats

    def clean(self):

        cleaned_data = super().clean()

        registration_start = cleaned_data.get("registration_start")
        registration_end = cleaned_data.get("registration_end")

        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if (
            registration_start
            and registration_end
            and registration_start >= registration_end
        ):
            self.add_error(
                "registration_end",
                "Registration end must be after registration start.",
            )

        if (
            start_date
            and end_date
            and start_date >= end_date
        ):
            self.add_error(
                "end_date",
                "Tournament end must be after tournament start.",
            )

        if (
            registration_end
            and start_date
            and registration_end > start_date
        ):
            self.add_error(
                "start_date",
                "Tournament cannot start before registration closes.",
            )

        return cleaned_data



class TournamentUpdateForm(TournamentCreateForm):
    pass


class TournamentRegistrationForm(forms.Form):
    """
    Allows a manager to choose one of their teams
    to register for a tournament.
    """

    team = forms.ModelChoiceField(
        queryset=Team.objects.none(),
        empty_label="Select Team",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["team"].queryset = Team.objects.filter(
            manager=user,
            is_active=True,
        ).order_by("name")


class MatchResultForm(forms.ModelForm):

    class Meta:
        model = Match
        fields = (
            "team_one_score",
            "team_two_score",
        )

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["team_one_score"].widget.attrs.update({
            "class": "form-control text-center",
            "min": 0,
        })

        self.fields["team_two_score"].widget.attrs.update({
            "class": "form-control text-center",
            "min": 0,
        })