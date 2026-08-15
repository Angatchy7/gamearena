from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth import get_user_model
from django.views import View
from django.views.generic import ListView
from django.contrib import messages

from .forms import TeamCreateForm, TeamUpdateForm, TeamInvitationForm
from .models import Team, TeamMember
from .services import create_team, update_team, send_team_invitation, get_team_profile_data, remove_team_member

User = get_user_model()


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


class MyTeamsView(LoginRequiredMixin, ListView):
    """
    Shows all teams where the logged-in user is the manager.
    """

    model = Team
    template_name = "teams/list.html"
    context_object_name = "teams"

    def get_queryset(self):
        return (
            Team.objects.filter(
                manager=self.request.user,
                is_active=True,
            )
            .exclude(description="__SOLO_INTERNAL__")
            .annotate(
                _active_member_count=Count("members", filter=Q(members__is_active=True), distinct=True)
            )
            .prefetch_related("members__user")
            .distinct()
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "My Teams"
        context["page_subtitle"] = "Teams you manage and own."
        context["empty_title"] = "You don't manage any teams yet."
        context["empty_subtitle"] = "Create your first esports team and start competing."
        context["is_my_teams"] = True
        return context


# Backward-compatible alias used by existing URL name "list"
TeamListView = MyTeamsView


class JoinedTeamsView(LoginRequiredMixin, ListView):
    """
    Shows teams where the user is an active member but NOT the manager.
    """

    model = Team
    template_name = "teams/joined.html"
    context_object_name = "teams"

    def get_queryset(self):
        return (
            Team.objects.filter(
                members__user=self.request.user,
                members__is_active=True,
                is_active=True,
            )
            .exclude(manager=self.request.user)
            .exclude(description="__SOLO_INTERNAL__")
            .annotate(
                _active_member_count=Count("members", filter=Q(members__is_active=True), distinct=True)
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


class RemoveTeamMemberView(LoginRequiredMixin, View):
    """
    Allows the team manager to soft-remove an active member.
    POST only. Manager cannot remove themselves.
    Returns 403 if the requester is not the manager.
    """

    def post(self, request, slug, member_id):
        team = get_object_or_404(Team, slug=slug)

        if request.user != team.manager:
            return HttpResponseForbidden("Only the team manager can remove members.")

        member_user = get_object_or_404(User, pk=member_id)

        result = remove_team_member(
            team=team,
            manager=request.user,
            member_user=member_user,
        )

        if result["success"]:
            messages.success(request, result["message"])
        else:
            messages.error(request, result["message"])

        return redirect("teams:detail", slug=team.slug)


class UserAutocompleteView(LoginRequiredMixin, View):
    """
    Returns non-sensitive JSON user suggestions for team invitations.
    Requires authentication and manager authorization.
    """

    def get(self, request, slug):
        team = get_object_or_404(Team, slug=slug)

        if request.user != team.manager:
            return JsonResponse({"error": "Unauthorized"}, status=403)

        q = request.GET.get("q", "").strip()
        if not q or len(q) < 1:
            return JsonResponse({"users": []})

        # Exclude active team members
        member_user_ids = team.members.filter(is_active=True).values_list(
            "user_id", flat=True
        )

        # Exclude users with pending invitations to this team
        from .models import TeamInvitation

        pending_invitee_ids = TeamInvitation.objects.filter(
            team=team,
            status=TeamInvitation.Status.PENDING,
        ).values_list("receiver_id", flat=True)

        excluded_ids = set(member_user_ids) | set(pending_invitee_ids)
        excluded_ids.add(team.manager_id)

        users_qs = (
            User.objects.filter(
                username__icontains=q,
                is_active=True,
            )
            .exclude(id__in=excluded_ids)
            .order_by("username")[:10]
        )

        users_data = [
            {
                "id": u.id,
                "username": u.username,
            }
            for u in users_qs
        ]

        return JsonResponse({"users": users_data})