from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views import View

from .models import (
    Tournament,
    TournamentRegistration,
    Round,
)

from .services import (
    publish_tournament,
    close_registration,
    generate_single_elimination_bracket,
)


class TournamentDashboardView(LoginRequiredMixin, View):

    template_name = "tournaments/dashboard.html"

    def get(self, request, slug):

        tournament = get_object_or_404(
            Tournament.objects.select_related(
                "champion",
            ),
            slug=slug,
            organizer=request.user,
        )

        registrations = (
            TournamentRegistration.objects
            .filter(
                tournament=tournament,
            )
            .select_related(
                "team",
                "registered_by",
            )
        )

        rounds = (
            Round.objects
            .filter(
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

        registration_percentage = 0

        if tournament.max_participants:

            registration_percentage = int(
                (
                    participant_count
                    / tournament.max_participants
                )
                * 100
            )

        completed_matches = 0
        pending_matches = 0

        for round_obj in rounds:

            completed_matches += (
                round_obj.matches.filter(
                    status="COMPLETED",
                ).count()
            )

            pending_matches += (
                round_obj.matches.exclude(
                    status="COMPLETED",
                ).count()
            )

        context = {

            "tournament": tournament,

            "registrations": registrations,

            "rounds": rounds,

            "participant_count": participant_count,

            "registration_percentage": registration_percentage,

            "completed_matches": completed_matches,

            "pending_matches": pending_matches,

        }

        return render(
            request,
            self.template_name,
            context,
        )


class TournamentParticipantsView(LoginRequiredMixin, View):

    template_name = "tournaments/participants.html"

    def get(self, request, slug):

        tournament = get_object_or_404(
            Tournament,
            slug=slug,
            organizer=request.user,
        )

        registrations = (
            TournamentRegistration.objects
            .filter(
                tournament=tournament,
            )
            .select_related(
                "team",
                "registered_by",
            )
            .order_by(
                "registered_at",
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


class TournamentPublishView(LoginRequiredMixin, View):

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
            "Tournament published successfully.",
        )

        return redirect(
            "tournaments:dashboard",
            slug=tournament.slug,
        )


class CloseRegistrationView(LoginRequiredMixin, View):

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
            "Registration closed successfully.",
        )

        return redirect(
            "tournaments:dashboard",
            slug=tournament.slug,
        )


class GenerateBracketView(LoginRequiredMixin, View):

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