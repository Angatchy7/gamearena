from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from .forms import TeamCreateForm, TeamUpdateForm, TeamInvitationForm
from .models import Team
from .services import create_team, update_team, send_team_invitation, get_team_profile_data


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

class TeamListView(LoginRequiredMixin, ListView):
    """
    Shows all teams where the logged-in user is a member.
    """

    model = Team

    template_name = "teams/list.html"

    context_object_name = "teams"

    def get_queryset(self):
        return (
            Team.objects.filter(
                members__user=self.request.user,
                members__is_active=True,
            )
            .prefetch_related("members__user")
            .distinct()
            .order_by("-created_at")
        )

class TeamDetailView(View):
    """
    Public team profile view showing statistics, active roster, tournaments, and recent matches.
    """

    template_name = "teams/detail.html"

    def get(self, request, slug):

        team = get_object_or_404(
            Team.objects.select_related("manager"),
            slug=slug,
        )

        context = get_team_profile_data(team=team)

        return render(
            request,
            self.template_name,
            context,
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

class TeamInviteView(LoginRequiredMixin, View):
    """
    Allows the team manager to invite a player.
    """

    template_name = "teams/invite.html"

    def get(self, request, slug):

        team = get_object_or_404(
            Team,
            slug=slug,
        )

        if request.user != team.manager:
            return redirect(
                "teams:detail",
                slug=team.slug,
            )

        form = TeamInvitationForm(
            team=team,
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

        if request.user != team.manager:
            return redirect(
                "teams:detail",
                slug=team.slug,
            )

        form = TeamInvitationForm(
            request.POST,
            team=team,
        )

        if form.is_valid():

            result = send_team_invitation(
                team=team,
                sender=request.user,
                receiver=form.cleaned_data["receiver"],
            )

            if result["success"]:
                return redirect(
                    "teams:detail",
                    slug=team.slug,
                )

            form.add_error(
                None,
                result["message"],
            )

        return render(
            request,
            self.template_name,
            {
                "team": team,
                "form": form,
            },
        )