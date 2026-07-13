from django import forms

from .models import Team


class TeamCreateForm(forms.ModelForm):
    class Meta:
        model = Team

        fields = (
            "name",
            "description",
            "logo",
            "max_players",
        )

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter team name",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter team description",
                }
            ),
            "logo": forms.FileInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "max_players": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "max": 10,
                }
            ),
        }


class TeamUpdateForm(forms.ModelForm):
    class Meta:
        model = Team

        fields = (
            "name",
            "description",
            "logo",
            "max_players",
        )

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter team name",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter team description",
                }
            ),
            "logo": forms.FileInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "max_players": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "max": 10,
                }
            ),
        }