# pyrefly: ignore [missing-import]
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.utils import timezone
# pyrefly: ignore [missing-import]
from apps.tournaments.models import Match, Round
from .permissions import require_tournament_manager
from .forms import TournamentRegistrationForm, MatchResultForm
from .models import TournamentRegistration, Tournament, Game
from django.contrib import messages
from django.db.models import Q, Count
from apps.teams.models import Team

from .forms import (
    TournamentCreateForm,
    TournamentUpdateForm,
)
from .services import (
    create_tournament,
    update_tournament,
    delete_tournament,
    publish_tournament,
    register_team,
    register_solo_player,
    close_registration,
    generate_single_elimination_bracket,
    advance_winner,
    get_tournament_statistics,
)


class TournamentListView(View):
    """
    Browse all tournaments with optional status/game/search filtering.
    """

    template_name = "tournaments/list.html"

    def get(self, request):

        query = request.GET.get("q", "").strip()
        game_slug = request.GET.get("game", "").strip()
        status_filter = request.GET.get("status", "").strip().lower()

        now = timezone.now()

        tournaments = (
            Tournament.objects
            .select_related(
                "game",
                "organizer",
            )
            .annotate(annotated_registered_count=Count("registrations", distinct=True))
            .order_by("-created_at")
        )

        if query:
            tournaments = tournaments.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(game__name__icontains=query)
            )

        if game_slug:
            tournaments = tournaments.filter(game__slug=game_slug)

        # Server-side status filter using ORM date comparisons
        if status_filter == "upcoming":
            # Published tournaments whose start hasn't arrived yet
            tournaments = tournaments.filter(
                start_date__gt=now,
            ).exclude(status__in=[Tournament.Status.CANCELLED, Tournament.Status.DRAFT])
        elif status_filter == "registration_open":
            # Registration window is active AND not cancelled
            tournaments = tournaments.filter(
                registration_start__lte=now,
                registration_end__gte=now,
                status=Tournament.Status.REGISTRATION_OPEN,
            )
        elif status_filter == "live":
            # Tournament has started but not ended, not cancelled
            tournaments = tournaments.filter(
                start_date__lte=now,
                end_date__gte=now,
            ).exclude(status__in=[Tournament.Status.CANCELLED, Tournament.Status.DRAFT])
        elif status_filter == "completed":
            tournaments = tournaments.filter(
                Q(status=Tournament.Status.COMPLETED) | Q(end_date__lt=now)
            ).exclude(status=Tournament.Status.CANCELLED)

        return render(
            request,
            self.template_name,
            {
                "page_title": "Browse Tournaments",
                "tournaments": tournaments,
                "games": Game.objects.filter(is_active=True).order_by("name"),
                "search_query": query,
                "selected_game": game_slug,
                "status_filter": status_filter,
            },
        )


class MyTournamentListView(LoginRequiredMixin, View):
    """
    Shows tournaments created by the logged-in user.
    """

    template_name = "tournaments/list.html"

    def get(self, request):

        query = request.GET.get("q", "").strip()
        game_slug = request.GET.get("game", "").strip()

        tournaments = (
            Tournament.objects.filter(
                organizer=request.user
            )
            .select_related(
                "game",
                "organizer",
            )
            .annotate(annotated_registered_count=Count("registrations", distinct=True))
            .order_by("-created_at")
        )

        if query:
            tournaments = tournaments.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(game__name__icontains=query)
            )

        if game_slug:
            tournaments = tournaments.filter(game__slug=game_slug)

        return render(
            request,
            self.template_name,
            {
                "page_title": "My Tournaments",
                "tournaments": tournaments,
                "games": Game.objects.filter(is_active=True).order_by("name"),
                "search_query": query,
                "selected_game": game_slug,
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

class TournamentBracketView(View):
    """
    Displays the tournament bracket.
    """

    template_name = "tournaments/brackets/fifa.html"

    def get(self, request, slug):

        tournament = get_object_or_404(
            Tournament,
            slug=slug,
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


class TournamentDetailView(View):
    """
    Displays tournament details.
    """

    template_name = "tournaments/detail.html"

    def get(self, request, slug):

        tournament = get_object_or_404(
            Tournament.objects.select_related(
                "game",
                "organizer",
                "champion",
            ),
            slug=slug,
        )

        context = get_tournament_statistics(tournament=tournament)

        return render(
            request,
            self.template_name,
            context,
        )

class TournamentParticipantsView(View):
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
    Organizer dashboard with complete tournament statistics.
    """

    template_name = "tournaments/dashboard.html"

    def get(self, request, slug):

        tournament = get_object_or_404(
            Tournament.objects.select_related(
                "game",
                "organizer",
                "champion",
            ),
            slug=slug,
            organizer=request.user,
        )

        context = get_tournament_statistics(tournament=tournament)

        return render(
            request,
            self.template_name,
            context,
        )


class TournamentStatisticsView(View):
    """
    Public page showing complete tournament statistics and team rankings.
    """

    template_name = "tournaments/statistics.html"

    def get(self, request, slug):

        tournament = get_object_or_404(
            Tournament.objects.select_related(
                "game",
                "organizer",
                "champion",
            ),
            slug=slug,
        )

        context = get_tournament_statistics(tournament=tournament)

        return render(
            request,
            self.template_name,
            context,
        )


class TournamentLeaderboardView(View):
    """
    Public page displaying the dynamic tournament leaderboard.
    """

    template_name = "tournaments/leaderboard.html"

    def get(self, request, slug):

        tournament = get_object_or_404(
            Tournament.objects.select_related(
                "game",
                "organizer",
                "champion",
            ),
            slug=slug,
        )

        context = get_tournament_statistics(tournament=tournament)

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
    Allows a team manager or solo player to register
    for a tournament.
    """

    template_name = "tournaments/register.html"

    def get(self, request, slug):

        tournament = get_object_or_404(
            Tournament,
            slug=slug,
        )

        if tournament.participation_type == Tournament.ParticipationType.SOLO:
            return render(
                request,
                self.template_name,
                {
                    "tournament": tournament,
                    "form": None,
                    "is_solo": True,
                },
            )

        form = TournamentRegistrationForm(
            user=request.user,
            tournament=tournament,
        )

        return render(
            request,
            self.template_name,
            {
                "tournament": tournament,
                "form": form,
                "is_solo": False,
            },
        )

    def post(self, request, slug):

        tournament = get_object_or_404(
            Tournament,
            slug=slug,
        )

        if tournament.participation_type == Tournament.ParticipationType.SOLO:
            result = register_solo_player(
                tournament=tournament,
                user=request.user,
            )

            if result["success"]:
                messages.success(request, "Registered successfully!")
                return redirect(
                    "tournaments:detail",
                    slug=tournament.slug,
                )

            return render(
                request,
                self.template_name,
                {
                    "tournament": tournament,
                    "form": None,
                    "is_solo": True,
                    "error_message": result["message"],
                },
            )

        form = TournamentRegistrationForm(
            request.POST,
            user=request.user,
            tournament=tournament,
        )

        if form.is_valid():

            result = register_team(
                tournament=tournament,
                team=form.cleaned_data["team"],
                user=request.user,
            )

            if result["success"]:
                messages.success(request, "Team registered successfully!")
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
                "is_solo": False,
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

class MatchWinnerUpdateView(LoginRequiredMixin, View):
    """
    Allows the organizer to declare the winner of a match by submitting scores.
    """

    def post(self, request, match_id):

        match = get_object_or_404(
            Match.objects.select_related(
                "round__tournament",
                "team_one",
                "team_two",
            ),
            id=match_id,
            round__tournament__organizer=request.user,
        )

        form = MatchResultForm(request.POST, instance=match)

        if form.is_valid():
            match = form.save(commit=False)

            if not match.team_one or not match.team_two:
                messages.error(
                    request,
                    "Both teams must be present to record match scores.",
                )
                return redirect(
                    "tournaments:match_detail",
                    pk=match.pk,
                )

            if match.team_one_score > match.team_two_score:
                match.winner = match.team_one
            elif match.team_two_score > match.team_one_score:
                match.winner = match.team_two
            else:
                messages.error(
                    request,
                    "Draws are not allowed. Scores must differ.",
                )
                return redirect(
                    "tournaments:match_detail",
                    pk=match.pk,
                )

            match.status = Match.Status.COMPLETED

            match.save()

            advance_winner(match=match)

            messages.success(
                request,
                "Winner updated successfully.",
            )

            return redirect(
                "tournaments:bracket",
                slug=match.round.tournament.slug,
            )

        messages.error(request, "Invalid score values.")
        return redirect(
            "tournaments:match_detail",
            pk=match.pk,
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

        messages.success(
            request,
            f"Tournament '{tournament.name}' published successfully! Registration is now open.",
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


class MatchDetailView(LoginRequiredMixin, View):

    template_name = "tournaments/match_detail.html"

    def get(self, request, pk):

        match = get_object_or_404(
            Match.objects.select_related(
                "round__tournament",
                "team_one",
                "team_two",
                "winner",
            ),
            pk=pk,
        )

        tournament = match.round.tournament
        form = MatchResultForm(instance=match)

        return render(
            request,
            self.template_name,
            {
                "match": match,
                "tournament": tournament,
                "form": form,
                "can_edit": request.user == tournament.organizer,
            },
        )

    def post(self, request, pk):

        match = get_object_or_404(
            Match.objects.select_related(
                "round__tournament",
                "team_one",
                "team_two",
            ),
            pk=pk,
        )

        tournament = match.round.tournament

        if tournament.organizer != request.user:
            raise PermissionDenied

        form = MatchResultForm(
            request.POST,
            instance=match,
        )

        if form.is_valid():

            match = form.save(commit=False)

            if not match.team_one or not match.team_two:
                form.add_error(
                    None,
                    "Both teams must be present to record match scores.",
                )
                return render(
                    request,
                    self.template_name,
                    {
                        "match": match,
                        "tournament": tournament,
                        "form": form,
                        "can_edit": True,
                    },
                )

            if match.team_one_score > match.team_two_score:

                match.winner = match.team_one

            elif match.team_two_score > match.team_one_score:

                match.winner = match.team_two

            else:

                form.add_error(
                    None,
                    "Tie scores are not allowed.",
                )

                return render(
                    request,
                    self.template_name,
                    {
                        "match": match,
                        "tournament": tournament,
                        "form": form,
                        "can_edit": True,
                    },
                )

            match.status = Match.Status.COMPLETED

            match.save()

            advance_winner(
                match=match,
            )

            messages.success(
                request,
                "Match completed successfully.",
            )

            return redirect(
                "tournaments:bracket",
                slug=match.round.tournament.slug,
            )

        return render(
            request,
            self.template_name,
            {
                "match": match,
                "tournament": tournament,
                "form": form,
                "can_edit": True,
            },
        )


class TournamentMatchesView(View):
    """
    Displays all matches for a tournament grouped by round.
    """

    template_name = "tournaments/matches.html"

    def get(self, request, slug):

        tournament = get_object_or_404(
            Tournament,
            slug=slug,
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