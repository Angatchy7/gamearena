from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from .permissions import require_tournament_manager

from .forms import (
    TournamentCreateForm,
    TournamentUpdateForm,
)
from .models import Tournament
from .services import (
    create_tournament,
    update_tournament,
    delete_tournament,
)


class TournamentListView(LoginRequiredMixin, View):
    """
    Displays all tournaments.
    """

    template_name = "tournaments/list.html"

    def get(self, request):

        tournaments = Tournament.objects.select_related(
            "game",
            "organizer",
        )

        return render(
            request,
            self.template_name,
            {
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