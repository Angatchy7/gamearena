from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import (
    get_object_or_404,
    render,
)
from django.views import View

from .models import (
    Tournament,
    Round,
)


class TournamentBracketView(LoginRequiredMixin, View):

    template_name = "tournaments/brackets/fifa.html"

    def get(self, request, slug):

        tournament = get_object_or_404(
            Tournament.objects.select_related(
                "champion",
                "organizer",
            ),
            slug=slug,
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
            .order_by(
                "order",
            )
        )

        bracket = []

        for round_obj in rounds:

            matches = list(
                round_obj.matches.all()
            )

            bracket.append(
                {
                    "round": round_obj,
                    "matches": matches,
                }
            )

        champion = tournament.champion

        context = {

            "tournament": tournament,

            "bracket": bracket,

            "champion": champion,

            "rounds": rounds,

        }

        return render(
            request,
            self.template_name,
            context,
        )