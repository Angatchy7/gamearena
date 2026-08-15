from django.db.models import Count
from django.shortcuts import render

from django.views import View
from django.db.models import Q

from apps.teams.models import Team
from apps.tournaments.models import Game, Tournament


def home(request):

    featured_tournament = (
        Tournament.objects
        .select_related("game", "organizer")
        .filter(status=Tournament.Status.LIVE)
        .first()
    )

    if featured_tournament is None:
        featured_tournament = (
            Tournament.objects
            .select_related("game", "organizer")
            .order_by("-created_at")
            .first()
        )

    live_tournaments = (
        Tournament.objects
        .select_related("game")
        .filter(status=Tournament.Status.LIVE)
        .order_by("-created_at")[:6]
    )

    upcoming_tournaments = (
        Tournament.objects
        .select_related("game")
        .filter(status=Tournament.Status.REGISTRATION_OPEN)
        .order_by("registration_end")[:6]
    )

    latest_tournaments = (
        Tournament.objects
        .select_related("game")
        .order_by("-created_at")[:6]
    )

    games = (
        Game.objects
        .annotate(
            total_tournaments=Count("tournaments")
        )
        .order_by("-total_tournaments", "name")
    )

    stats = {
        "tournaments": Tournament.objects.count(),
        "teams": Team.objects.exclude(description="__SOLO_INTERNAL__").count(),
        "games": Game.objects.count(),
    }

    return render(
    request,
    "core/home.html",
    {
        "featured_tournament": featured_tournament,
        "live_tournaments": live_tournaments,
        "upcoming_tournaments": upcoming_tournaments,
        "latest_tournaments": latest_tournaments,
        "games": games,
        "stats": stats,

        # Hero Stats
        "tournament_count": stats["tournaments"],
        "team_count": stats["teams"],
        "game_count": stats["games"],

        # Layout
        "show_sidebar": False,
    },
)

class SearchView(View):
    """
    Global search for tournaments, teams and games.
    """

    template_name = "core/search.html"

    def get(self, request):

        query = request.GET.get(
            "q",
            "",
        ).strip()

        tournaments = Tournament.objects.none()
        teams = Team.objects.none()
        games = Game.objects.none()

        if query:

            tournaments = (
                Tournament.objects
                .select_related(
                    "game",
                    "organizer",
                )
                .filter(
                    Q(name__icontains=query)
                    | Q(description__icontains=query)
                )
                .order_by("-created_at")
            )

            teams = (
                Team.objects
                .exclude(description="__SOLO_INTERNAL__")
                .filter(
                    Q(name__icontains=query)
                    | Q(description__icontains=query)
                )
                .order_by("name")
            )

            games = (
                Game.objects
                .filter(
                    name__icontains=query
                )
                .order_by("name")
            )

        return render(
            request,
            self.template_name,
            {
                "query": query,
                "tournaments": tournaments,
                "teams": teams,
                "games": games,
                "show_sidebar": True,
            },
        )


from django.http import JsonResponse


class SearchAjaxView(View):

    def get(self, request):

        query = request.GET.get("q", "").strip()

        if len(query) < 2:
            return JsonResponse(
                {
                    "tournaments": [],
                    "teams": [],
                    "games": [],
                }
            )

        tournaments = (
            Tournament.objects
            .select_related("game")
            .filter(name__icontains=query)
            .order_by("-created_at")[:4]
        )

        teams = (
            Team.objects
            .exclude(description="__SOLO_INTERNAL__")
            .filter(name__icontains=query)
            .order_by("name")[:4]
        )

        games = (
            Game.objects
            .filter(name__icontains=query)
            .order_by("name")[:4]
        )

        return JsonResponse({

            "tournaments": [
                {
                    "name": t.name,
                    "slug": t.slug,
                    "game": t.game.name,
                    "status": t.get_status_display(),

                    "prize_pool": t.prize_pool,

                    "start_date": (
                        t.start_date.strftime("%d %b %Y")
                        if t.start_date else "TBA"
                    ),

                    "registration_end": (
                        t.registration_end.strftime("%d %b %Y")
                        if t.registration_end else "N/A"
                    ),

                    "url": f"/tournaments/{t.slug}/",
                }
                for t in tournaments
            ],

            "teams": [
                {
                    "name": team.name,
                    "manager": team.manager.username,
                    "url": f"/teams/{team.slug}/",
                }
                for team in teams
            ],

            "games": [
                {
                    "name": game.name,
                    "tournaments": game.tournaments.count(),
                }
                for game in games
            ],

        })


class GameCatalogView(View):
    """
    Standalone Games catalog page listing all registered game types,
    with artwork, tournament counts, and direct Explore links.
    """

    template_name = "core/games.html"

    def get(self, request):
        games = (
            Game.objects
            .annotate(total_tournaments=Count("tournaments"))
            .order_by("-total_tournaments", "name")
        )
        return render(
            request,
            self.template_name,
            {
                "games": games,
                "show_sidebar": True,
            },
        )