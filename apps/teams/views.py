from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .forms import TeamCreateForm, TeamUpdateForm
from .models import Team
from .services import create_team, update_team


class CreateTeamView(LoginRequiredMixin, View):
    """
    Allows a manager to create a team.
    """

    template_name = "teams/create_team.html"

    def get(self, request):
        form = TeamCreateForm()
        return render(
            request,
            self.template_name,
            {"form": form},
        )

    def post(self, request):
        form = TeamCreateForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            result = create_team(
                manager=request.user,
                form=form,
            )

            if result["success"]:
                return redirect(
                    "teams:detail",
                    slug=result["team"].slug,
                )

            form.add_error(
                None,
                result["message"],
            )

        return render(
            request,
            self.template_name,
            {"form": form},
        )


class TeamDetailView(LoginRequiredMixin, View):

    template_name = "teams/detail.html"

    def get(self, request, slug):

        team = get_object_or_404(
            Team.objects.prefetch_related(
                "members__user",
            ),
            slug=slug,
        )

        return render(
            request,
            self.template_name,
            {
                "team": team,
            },
        )


class TeamUpdateView(LoginRequiredMixin, View):

    template_name = "teams/edit_team.html"

    def get(self, request, slug):

        team = get_object_or_404(
            Team,
            slug=slug,
        )

        form = TeamUpdateForm(
            instance=team,
        )

        return render(
            request,
            self.template_name,
            {
                "team": team,
                "form": form,
            },
        )

    def post(self, request, slug):

        team = get_object_or_404(
            Team,
            slug=slug,
        )

        form = TeamUpdateForm(
            request.POST,
            request.FILES,
            instance=team,
        )

        if form.is_valid():

            result = update_team(
                team=team,
                form=form,
            )

            return redirect(
                "teams:detail",
                slug=result["team"].slug,
            )

        return render(
            request,
            self.template_name,
            {
                "team": team,
                "form": form,
            },
        )