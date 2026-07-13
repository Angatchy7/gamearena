from django import forms

from .models import Tournament


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
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                }
            ),
            "registration_end": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                }
            ),
            "start_date": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                }
            ),
            "end_date": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                }
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


class TournamentUpdateForm(TournamentCreateForm):
    pass