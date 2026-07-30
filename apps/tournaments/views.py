from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from .permissions import require_tournament_manager
from .forms import TournamentRegistrationForm
from .models import TournamentRegistration
from .services import register_team, publish_tournament
from .models import TournamentRegistration
from django.contrib import messages
# pyrefly: ignore [missing-import]
from apps.tournaments.models import Round

from .forms import (
    TournamentCreateForm,
    TournamentUpdateForm,
)
from .models import Tournament
from .services import (
    create_tournament,
    update_tournament,
    delete_tournament,
    publish_tournament,
    register_team,
    close_registration,
    generate_single_elimination_bracket,
)


class TournamentListView(LoginRequiredMixin, View):
    """
    Browse all tournaments.
    """

    template_name = "tournaments/list.html"

    def get(self, request):

        tournaments = (
            Tournament.objects
            .select_related(
                "game",
                "organizer",
            )
            .order_by("-created_at")
        )

        return render(
            request,
            self.template_name,
            {
                "page_title": "Browse Tournaments",
                "tournaments": tournaments,
            },
        )

class MyTournamentListView(LoginRequiredMixin, View):
    """
    Shows tournaments created by the logged-in user.
    """

    template_name = "tournaments/list.html"

    def get(self, request):

        tournaments = (
            Tournament.objects.filter(
                organizer=request.user
            )
            .select_related(
                "game",
                "organizer",
            )
            .order_by("-created_at")
        )

        return render(
            request,
            self.template_name,
            {
                "page_title": "My Tournaments",
                "tournaments": tournaments,
            },
        )

class TournamentCreateView(LoginRequiredMixin, View):
    """
    Allows a user to create a tournament.
    """

    template_name = "tournaments/create.html"

    def get(self, request):

        form = TournamentCreateForm()

        return render(
            request,
            self.template_name,
            {
                "form": form,
            },
        )

    def post(self, request):

        form = TournamentCreateForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            tournament = create_tournament(
                organizer=request.user,
                form=form,
            )

            return redirect(
                "tournaments:detail",
                slug=tournament.slug,
            )

        return render(
            request,
            self.template_name,
            {
                "form": form,
            },
        )

class TournamentBracketView(LoginRequiredMixin, View):
    """
    Displays the tournament bracket.
    """

    template_name = "tournaments/bracket.html"

    def get(self, request, slug):

        tournament = get_object_or_404(
            Tournament,
            slug=slug,
            organizer=request.user,
        )

        rounds = (
            Round.objects.filter(
                tournament=tournament,
            )
            .prefetch_related(
                "matches__team_one",
                "matches__team_two",
                "matches__winner",
            )
            .order_by("order")
        )

        return render(
            request,
            self.template_name,
            {
                "tournament": tournament,
                "rounds": rounds,
            },
        )

        
class TournamentDetailView(LoginRequiredMixin, View):
    """
    Displays tournament details.
    """

    template_name = "tournaments/detail.html"

    def get(self, request, slug):

        tournament = get_object_or_404(
            Tournament.objects.select_related(
                "game",
                "organizer",
            ),
            slug=slug,
        )

        return render(
            request,
            self.template_name,
            {
                "tournament": tournament,
            },
        )

class TournamentParticipantsView(LoginRequiredMixin, View):
    """
    Displays all registered participants of a tournament.
    """

    template_name = "tournaments/participants.html"

    def get(self, request, slug):

        tournament = get_object_or_404(
            Tournament,
            slug=slug,
        )

        registrations = (
            TournamentRegistration.objects
            .filter(tournament=tournament)
            .select_related(
                "team",
                "registered_by",
            )
            .prefetch_related(
                "team__members__user",
            )
        )

        return render(
            request,
            self.template_name,
            {
                "tournament": tournament,
                "registrations": registrations,
            },
        )

class TournamentDashboardView(LoginRequiredMixin, View):
    """
    Organizer dashboard.
    """

    template_name = "tournaments/dashboard.html"

    def get(self, request, slug):

        tournament = get_object_or_404(
            Tournament,
            slug=slug,
            organizer=request.user,
        )

        registrations = (
            TournamentRegistration.objects.filter(
                tournament=tournament,
            ).select_related("team")
        )

        rounds = (
            Round.objects.filter(
                tournament=tournament,
            )
            .prefetch_related(
                "matches__team_one",
                "matches__team_two",
                "matches__winner",
            )
            .order_by("order")
        )

        participant_count = registrations.count()

        registration_percentage = (
            int(
                participant_count
                * 100
                / tournament.max_participants
            )
            if tournament.max_participants > 0
            else 0
        )

        context = {

            "tournament": tournament,

            "registrations": registrations,

            "participant_count": participant_count,

            "registration_percentage": registration_percentage,

            "rounds": rounds,

        }

        return render(
            request,
            self.template_name,
            context,
        )

class CloseRegistrationView(LoginRequiredMixin, View):
    """
    Allows the organizer to close tournament registration.
    """

    def post(self, request, slug):

        tournament = get_object_or_404(
            Tournament,
            slug=slug,
            organizer=request.user,
        )

        close_registration(
            tournament=tournament,
        )

        messages.success(
            request,
            "Tournament registration has been closed successfully.",
        )

        return redirect(
            "tournaments:dashboard",
            slug=tournament.slug,
        )

class GenerateBracketView(LoginRequiredMixin, View):
    """
    Generates the tournament bracket.
    """

    def post(self, request, slug):

        tournament = get_object_or_404(
            Tournament,
            slug=slug,
            organizer=request.user,
        )

        result = generate_single_elimination_bracket(
            tournament=tournament,
        )

        if result["success"]:

            messages.success(
                request,
                "Bracket generated successfully.",
            )

        else:

            messages.error(
                request,
                result["message"],
            )

        return redirect(
            "tournaments:dashboard",
            slug=tournament.slug,
        )

        
class TournamentRegisterView(LoginRequiredMixin, View):
    """
    Allows a team manager to register one of their teams
    for a tournament.
    """

    template_name = "tournaments/register.html"

    def get(self, request, slug):

        tournament = get_object_or_404(
            Tournament,
            slug=slug,
        )

        form = TournamentRegistrationForm(
            user=request.user,
        )

        return render(
            request,
            self.template_name,
            {
                "tournament": tournament,
                "form": form,
            },
        )

    def post(self, request, slug):

        tournament = get_object_or_404(
            Tournament,
            slug=slug,
        )

        form = TournamentRegistrationForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():

            result = register_team(
                tournament=tournament,
                team=form.cleaned_data["team"],
                user=request.user,
            )

            if result["success"]:
                return redirect(
                    "tournaments:detail",
                    slug=tournament.slug,
                )

            form.add_error(
                None,
                result["message"],
            )

        return render(
            request,
            self.template_name,
            {
                "tournament": tournament,
                "form": form,
            },
        )


class TournamentUpdateView(LoginRequiredMixin, View):
    """
    Allows the organizer to edit a tournament.
    """

    template_name = "tournaments/edit.html"

    def get(self, request, slug):

        tournament = get_object_or_404(
            Tournament,
            slug=slug,
        )

        require_tournament_manager(
            request.user,
            tournament,
        )

        form = TournamentUpdateForm(
            instance=tournament,
        )

        return render(
            request,
            self.template_name,
            {
                "tournament": tournament,
                "form": form,
            },
        )

    def post(self, request, slug):

        tournament = get_object_or_404(
            Tournament,
            slug=slug,
        )

        require_tournament_manager(
            request.user,
            tournament,
        )

        form = TournamentUpdateForm(
            request.POST,
            request.FILES,
            instance=tournament,
        )

        if form.is_valid():

            update_tournament(
                tournament=tournament,
                form=form,
            )

            return redirect(
                "tournaments:detail",
                slug=tournament.slug,
            )

        return render(
            request,
            self.template_name,
            {
                "tournament": tournament,
                "form": form,
            },
        )

class TournamentPublishView(LoginRequiredMixin, View):
    """
    Opens tournament registration.
    """

    def post(self, request, slug):

        tournament = get_object_or_404(
            Tournament,
            slug=slug,
            organizer=request.user,
        )

        publish_tournament(
            tournament=tournament,
        )

        return redirect(
            "tournaments:detail",
            slug=tournament.slug,
        )


class TournamentDeleteView(LoginRequiredMixin, View):
    """
    Deletes a tournament.
    """

    template_name = "tournaments/delete.html"

    def get(self, request, slug):

        tournament = get_object_or_404(
            Tournament,
            slug=slug,
        )

        require_tournament_manager(
            request.user,
            tournament,
        )

        return render(
            request,
            self.template_name,
            {
                "tournament": tournament,
            },
        )

    def post(self, request, slug):

        tournament = get_object_or_404(
            Tournament,
            slug=slug,
        )

        require_tournament_manager(
            request.user,
            tournament,
        )

        delete_tournament(
            tournament=tournament,
        )

        return redirect(
            "tournaments:list",
        )