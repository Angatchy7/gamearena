from django.db.models import Q
from apps.teams.models import TeamMember
from apps.tournaments.models import TournamentRegistration, Match, Tournament


def get_player_profile(*, user):
    """
    Computes complete player profile data including teams, matches, tournament history,
    wins/losses/win_rate, recent matches, and dynamically computed achievements.
    """

    memberships = (
        TeamMember.objects.filter(user=user, is_active=True)
        .exclude(team__description="__SOLO_INTERNAL__")
        .select_related("team")
        .order_by("-joined_at")
    )
    user_teams = [m.team for m in memberships]

    registrations = (
        TournamentRegistration.objects.filter(
            Q(team__in=user_teams)
            | Q(user=user)
            | Q(registered_by=user, tournament__participation_type=Tournament.ParticipationType.SOLO)
        )
        .select_related("tournament", "tournament__game", "team")
        .order_by("-registered_at")
    )

    tournaments_dict = {}
    for reg in registrations:
        if reg.tournament.id not in tournaments_dict:
            tournaments_dict[reg.tournament.id] = {
                "tournament": reg.tournament,
                "team": reg.team if reg.team and reg.team.description != "__SOLO_INTERNAL__" else None,
            }
    tournament_history = list(tournaments_dict.values())

    all_user_matches = list(
        Match.objects.filter(
            Q(team_one__in=user_teams) | Q(team_two__in=user_teams)
        )
        .select_related("round__tournament", "team_one", "team_two", "winner")
        .order_by("-id")
    )

    completed_matches = [
        m for m in all_user_matches if m.status == Match.Status.COMPLETED and m.team_one and m.team_two
    ]

    wins = sum(1 for m in completed_matches if m.winner in user_teams)
    losses = sum(
        1 for m in completed_matches if m.winner and m.winner not in user_teams
    )
    matches_played = len(completed_matches)

    win_rate = (
        round((wins / matches_played) * 100, 1)
        if matches_played > 0
        else 0.0
    )

    processed_recent_matches = []
    for match in all_user_matches[:10]:
        user_team_in_match = (
            match.team_one if match.team_one in user_teams else match.team_two
        )
        opponent = (
            match.team_two if match.team_one in user_teams else match.team_one
        )

        is_team_one = match.team_one == user_team_in_match
        user_score = (
            match.team_one_score if is_team_one else match.team_two_score
        )
        opponent_score = (
            match.team_two_score if is_team_one else match.team_one_score
        )
        is_winner = (
            (match.winner == user_team_in_match) if match.winner else False
        )

        processed_recent_matches.append(
            {
                "match": match,
                "tournament": match.round.tournament,
                "user_team": user_team_in_match,
                "opponent": opponent,
                "user_score": user_score,
                "opponent_score": opponent_score,
                "is_winner": is_winner,
                "is_completed": (match.status == Match.Status.COMPLETED),
            }
        )

    # Achievements computation
    achievements = []
    championship_count = Tournament.objects.filter(
        champion__in=user_teams
    ).count()
    if championship_count > 0:
        achievements.append(
            {
                "title": "Tournament Champion",
                "icon": "🏆",
                "badge_class": "bg-warning text-dark",
                "description": f"Won {championship_count} tournament championship(s)",
            }
        )

    if any(
        m.team_role
        in [TeamMember.TeamRole.MANAGER, TeamMember.TeamRole.IGL]
        for m in memberships
    ):
        achievements.append(
            {
                "title": "Team Leader",
                "icon": "🛡️",
                "badge_class": "bg-primary text-white",
                "description": "Serves as Team Manager or In-Game Leader",
            }
        )

    if matches_played >= 5:
        achievements.append(
            {
                "title": "Veteran Competitor",
                "icon": "⚡",
                "badge_class": "bg-info text-white",
                "description": f"Completed {matches_played} official matches",
            }
        )

    if win_rate >= 60.0 and matches_played >= 3:
        achievements.append(
            {
                "title": "Sharpshooter",
                "icon": "🎯",
                "badge_class": "bg-success text-white",
                "description": f"Maintained a high win rate of {win_rate}%",
            }
        )

    if len(tournament_history) >= 2:
        achievements.append(
            {
                "title": "Seasoned Contender",
                "icon": "🎮",
                "badge_class": "bg-secondary text-white",
                "description": f"Participated in {len(tournament_history)} tournaments",
            }
        )

    return {
        "player": user,
        "memberships": memberships,
        "user_teams": user_teams,
        "tournament_history": tournament_history,
        "wins": wins,
        "losses": losses,
        "matches_played": matches_played,
        "win_rate": win_rate,
        "recent_matches": processed_recent_matches,
        "achievements": achievements,
    }
