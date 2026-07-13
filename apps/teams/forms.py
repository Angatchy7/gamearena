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
                    "placeholder": "Team Name",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe your team...",
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
                    "min": 2,
                    "max": 20,
                }
            ),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if Team.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError(
                "A team with this name already exists."
            )

        return name


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
                    "placeholder": "Team Name",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe your team...",
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
                    "min": 2,
                    "max": 20,
                }
            ),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if (
            Team.objects.filter(name__iexact=name)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError(
                "A team with this name already exists."
            )

        return name