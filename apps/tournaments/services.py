from django.db import transaction
from django.utils import timezone
import random
import math

from .models import Tournament, Round, Match
from .models import TournamentRegistration
# pyrefly: ignore [missing-import]
from apps.teams.models import Team, TeamMember


@transaction.atomic
def create_tournament(*, organizer, form):
    """
    Creates a tournament.
    """

    tournament = form.save(commit=False)

    tournament.organizer = organizer

    tournament.save()

    return tournament


@transaction.atomic
def update_tournament(*, tournament, form):
    """
    Updates an existing tournament.
    """

    tournament.name = form.cleaned_data["name"]
    tournament.game = form.cleaned_data["game"]
    tournament.description = form.cleaned_data["description"]
    tournament.rules = form.cleaned_data["rules"]

    tournament.tournament_type = form.cleaned_data["tournament_type"]
    tournament.participation_type = form.cleaned_data["participation_type"]

    tournament.team_size = form.cleaned_data["team_size"]
    tournament.max_participants = form.cleaned_data["max_participants"]

    tournament.registration_fee = form.cleaned_data["registration_fee"]
    tournament.prize_pool = form.cleaned_data["prize_pool"]

    tournament.registration_start = form.cleaned_data["registration_start"]
    tournament.registration_end = form.cleaned_data["registration_end"]

    tournament.start_date = form.cleaned_data["start_date"]
    tournament.end_date = form.cleaned_data["end_date"]

    tournament.contact_email = form.cleaned_data["contact_email"]
    tournament.discord_link = form.cleaned_data["discord_link"]

    tournament.visibility = form.cleaned_data["visibility"]

    if form.cleaned_data.get("banner"):
        tournament.banner = form.cleaned_data["banner"]

    if form.cleaned_data.get("cover_image"):
        tournament.cover_image = form.cleaned_data["cover_image"]

    tournament.save()

    return tournament


@transaction.atomic
def delete_tournament(*, tournament):
    """
    Deletes a tournament.
    """

    tournament.delete()


@transaction.atomic
def open_registration(*, tournament):

    tournament.status = Tournament.Status.REGISTRATION_OPEN

    tournament.save(update_fields=["status"])


@transaction.atomic
def close_registration(*, tournament):

    tournament.status = Tournament.Status.REGISTRATION_CLOSED

    tournament.save(update_fields=["status"])


@transaction.atomic
def publish_tournament(*, tournament):
    """
    Publishes a tournament by opening registration.
    """

    tournament.status = Tournament.Status.REGISTRATION_OPEN

    tournament.save(
        update_fields=["status"],
    )


@transaction.atomic
def cancel_tournament(*, tournament):

    tournament.status = Tournament.Status.CANCELLED

    tournament.save(update_fields=["status"])




@transaction.atomic
def register_team(
    *,
    tournament,
    team,
    user,
):
    """
    Registers a team in a tournament.
    """

    if tournament.participation_type != tournament.ParticipationType.TEAM:
        return {
            "success": False,
            "message": "This is not a team tournament.",
        }

    if not tournament.is_registration_open:
        return {
            "success": False,
            "message": "Tournament registration is closed.",
        }

    if team.manager != user:
        return {
            "success": False,
            "message": "Only the team manager can register the team.",
        }

    if team.game_id and tournament.game_id and team.game_id != tournament.game_id:
        return {
            "success": False,
            "message": "Team game does not match tournament game.",
        }

    # Lock tournament row for atomic capacity check & race condition safety
    Tournament.objects.select_for_update().get(pk=tournament.pk)

    if TournamentRegistration.objects.filter(
        tournament=tournament,
        team=team,
    ).exists():
        return {
            "success": False,
            "message": "Team is already registered.",
        }

    if not team.is_active:
        return {
            "success": False,
            "message": "This team is inactive.",
        }

    # Player overlap check: A player cannot participate in two different teams in the SAME tournament.
    new_team_player_ids = set(
        TeamMember.objects.filter(
            team=team,
            is_active=True,
        ).values_list("user_id", flat=True)
    )

    registered_team_ids = TournamentRegistration.objects.filter(
        tournament=tournament,
        team__isnull=False,
    ).values_list("team_id", flat=True)

    if TeamMember.objects.filter(
        team_id__in=registered_team_ids,
        user_id__in=new_team_player_ids,
        is_active=True,
    ).exists():
        return {
            "success": False,
            "message": "One or more players are already registered with another team in this tournament.",
        }

    active_players = len(new_team_player_ids)

    if active_players < tournament.team_size:
        return {
            "success": False,
            "message": (
                f"This tournament requires {tournament.team_size} players.\n"
                f"Your team currently has {active_players} active players."
            ),
        }

    participant_count = TournamentRegistration.objects.filter(
        tournament=tournament,
    ).count()

    if participant_count >= tournament.max_participants:
        return {
            "success": False,
            "message": "Tournament is already full.",
        }

    registration = TournamentRegistration.objects.create(
        tournament=tournament,
        team=team,
        registered_by=user,
    )

    return {
        "success": True,
        "registration": registration,
    }


@transaction.atomic
def register_solo_player(
    *,
    tournament,
    user,
):
    """
    Registers an individual player in a SOLO tournament.
    """

    if tournament.participation_type != Tournament.ParticipationType.SOLO:
        return {
            "success": False,
            "message": "This is not a solo tournament.",
        }

    if not tournament.is_registration_open:
        return {
            "success": False,
            "message": "Tournament registration is closed.",
        }

    # Lock tournament row for atomic capacity check & race condition safety
    Tournament.objects.select_for_update().get(pk=tournament.pk)

    if (
        TournamentRegistration.objects.filter(
            tournament=tournament,
            user=user,
        ).exists()
        or TournamentRegistration.objects.filter(
            tournament=tournament,
            registered_by=user,
        ).exists()
    ):
        return {
            "success": False,
            "message": "You are already registered for this tournament.",
        }

    participant_count = TournamentRegistration.objects.filter(
        tournament=tournament,
    ).count()

    if participant_count >= tournament.max_participants:
        return {
            "success": False,
            "message": "Tournament is already full.",
        }

    # Internal solo team representation for bracket & match compatibility
    solo_team, _ = Team.objects.get_or_create(
        name=f"__SOLO_{user.username}_{tournament.pk}__",
        manager=user,
        defaults={
            "game": tournament.game,
            "description": "__SOLO_INTERNAL__",
            "is_active": False,  # Hide from public team listings
            "max_players": 1,
        },
    )

    TeamMember.objects.get_or_create(
        team=solo_team,
        user=user,
        defaults={
            "is_active": True,
            "team_role": TeamMember.TeamRole.PLAYER,
        },
    )

    registration = TournamentRegistration.objects.create(
        tournament=tournament,
        team=solo_team,
        user=user,
        registered_by=user,
    )

    return {
        "success": True,
        "registration": registration,
    }


@transaction.atomic
def generate_single_elimination_bracket(*, tournament):
    """
    Generates a compact smart single elimination bracket based on participant count.
    Supports odd counts with randomized single-BYE per round, without power-of-two padding.
    """

    registrations = list(
        TournamentRegistration.objects.filter(
            tournament=tournament,
        ).select_related("team")
    )

    if len(registrations) < 2:
        return {
            "success": False,
            "message": "At least two teams are required.",
        }

    # Prevent generating twice
    if Round.objects.filter(tournament=tournament).exists():
        return {
            "success": False,
            "message": "Bracket already exists.",
        }

    random.shuffle(registrations)
    real_teams = [r.team for r in registrations]

    # Calculate compact round structure from Round 1 to Final
    current_count = len(real_teams)
    round_structures = []

    while current_count > 1:
        if current_count % 2 == 0:
            num_real = current_count // 2
            has_bye = False
            total_matches = num_real
            next_count = num_real
        else:
            num_real = (current_count - 1) // 2
            has_bye = True
            total_matches = num_real + 1
            next_count = num_real + 1

        round_structures.append({
            "in_count": current_count,
            "real_matches": num_real,
            "has_bye": has_bye,
            "total_matches": total_matches,
            "next_count": next_count,
        })
        current_count = next_count

    # Create Round and Match objects in database
    for r_idx, struct in enumerate(round_structures):
        round_obj = Round.objects.create(
            tournament=tournament,
            name=f"Round {r_idx + 1}",
            order=r_idx + 1,
        )
        struct["round_obj"] = round_obj
        struct["matches"] = []
        for m_idx in range(struct["total_matches"]):
            match_obj = Match.objects.create(
                round=round_obj,
                match_number=m_idx + 1,
            )
            struct["matches"].append(match_obj)

    # Populate Round 1 pairings
    round1_struct = round_structures[0]
    teams = list(real_teams)
    bye_team = None

    if round1_struct["has_bye"]:
        bye_idx = random.randrange(len(teams))
        bye_team = teams.pop(bye_idx)

    # Real matches in Round 1
    for m_idx in range(round1_struct["real_matches"]):
        match_obj = round1_struct["matches"][m_idx]
        match_obj.team_one = teams[2 * m_idx]
        match_obj.team_two = teams[2 * m_idx + 1]
        match_obj.save()

    # BYE match in Round 1
    bye_match_r1 = None
    if bye_team is not None:
        bye_match_r1 = round1_struct["matches"][-1]
        bye_match_r1.team_one = bye_team
        bye_match_r1.team_two = None
        bye_match_r1.is_bye = True
        bye_match_r1.winner = bye_team
        bye_match_r1.status = Match.Status.COMPLETED
        bye_match_r1.save()

    # Connect matches across consecutive rounds
    for r_idx in range(len(round_structures) - 1):
        curr_struct = round_structures[r_idx]
        next_struct = round_structures[r_idx + 1]

        curr_matches = curr_struct["matches"]
        next_matches = next_struct["matches"]

        path_indices = list(range(len(curr_matches)))

        if next_struct["has_bye"]:
            # Pick one path randomly to receive BYE in next round
            bye_pos = random.randrange(len(path_indices))
            bye_path_idx = path_indices.pop(bye_pos)

            next_bye_match = next_matches[-1]
            next_bye_match.is_bye = True
            next_bye_match.save(update_fields=["is_bye"])

            src_match = curr_matches[bye_path_idx]
            src_match.next_match = next_bye_match
            src_match.next_match_slot = 1
            src_match.save(update_fields=["next_match", "next_match_slot"])

        # Shuffle remaining path indices before pairing into next round's real matches
        random.shuffle(path_indices)
        for p_idx in range(next_struct["real_matches"]):
            src1 = curr_matches[path_indices[2 * p_idx]]
            src2 = curr_matches[path_indices[2 * p_idx + 1]]
            target_match = next_matches[p_idx]

            src1.next_match = target_match
            src1.next_match_slot = 1
            src1.save(update_fields=["next_match", "next_match_slot"])

            src2.next_match = target_match
            src2.next_match_slot = 2
            src2.save(update_fields=["next_match", "next_match_slot"])

    # Auto-advance Round 1 BYE participant
    if bye_match_r1:
        advance_winner(match=bye_match_r1)

    return {
        "success": True,
    }


@transaction.atomic
def advance_winner(*, match):
    """
    Advances the winner to the next round.
    Declares champion when the final match is completed.
    """

    if match.winner is None:
        return

    tournament = match.round.tournament
    current_round = match.round

    next_round = Round.objects.filter(
        tournament=tournament,
        order=current_round.order + 1,
    ).first()

    # Final round completion
    if next_round is None:

        tournament.champion = match.winner
        tournament.status = Tournament.Status.COMPLETED

        tournament.save(
            update_fields=[
                "champion",
                "status",
            ]
        )

        return

    if match.next_match_id:
        next_match = match.next_match
        if match.next_match_slot == 1:
            next_match.team_one = match.winner
        else:
            next_match.team_two = match.winner
        next_match.save(update_fields=["team_one", "team_two"])
    else:
        # Fallback for historical tournaments created before next_match field was populated
        next_match_number = math.ceil(
            match.match_number / 2
        )
        try:
            next_match = Match.objects.get(
                round=next_round,
                match_number=next_match_number,
            )
            if match.match_number % 2 == 1:
                next_match.team_one = match.winner
            else:
                next_match.team_two = match.winner

            next_match.save(
                update_fields=[
                    "team_one",
                    "team_two",
                ]
            )
        except Match.DoesNotExist:
            return

    # Auto-complete if next_match is a designated BYE match
    if next_match.is_bye and (next_match.team_one or next_match.team_two) and next_match.status != Match.Status.COMPLETED:
        bye_winner = next_match.team_one or next_match.team_two
        next_match.winner = bye_winner
        next_match.status = Match.Status.COMPLETED
        next_match.save(update_fields=["winner", "status"])
        advance_winner(match=next_match)


def get_tournament_statistics(*, tournament):
    """
    Calculates summary, performance metrics, and team rankings for a tournament.
    """

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

    all_matches = list(
        Match.objects.filter(
            round__tournament=tournament,
        )
        .select_related(
            "round",
            "team_one",
            "team_two",
            "winner",
        )
        .order_by("round__order", "match_number")
    )

    participant_count = registrations.count()
    total_matches_count = len(all_matches)

    completed_matches = [
        m for m in all_matches if m.status == Match.Status.COMPLETED
    ]
    completed_matches_count = len(completed_matches)
    remaining_matches_count = total_matches_count - completed_matches_count

    played_matches = [
        m for m in completed_matches if m.team_one and m.team_two
    ]

    completion_percentage = (
        int((completed_matches_count / total_matches_count) * 100)
        if total_matches_count > 0
        else 0
    )

    registration_percentage = (
        int((participant_count / tournament.max_participants) * 100)
        if tournament.max_participants > 0
        else 0
    )

    # Performance Statistics
    total_goals = sum(
        m.team_one_score + m.team_two_score for m in played_matches
    )
    avg_goals = (
        round(total_goals / len(played_matches), 2)
        if len(played_matches) > 0
        else 0
    )

    highest_scoring_match = None
    if played_matches:
        highest_scoring_match = max(
            played_matches,
            key=lambda m: m.team_one_score + m.team_two_score,
        )

    first_completed_match = played_matches[0] if played_matches else None
    last_completed_match = played_matches[-1] if played_matches else None

    # Team / Player Rankings
    team_stats = {}
    for reg in registrations:
        if not reg.team:
            continue
        team_stats[reg.team.id] = {
            "team": reg.team,
            "display_name": reg.display_name,
            "wins": 0,
            "losses": 0,
            "matches_played": 0,
            "goals_scored": 0,
            "goals_conceded": 0,
            "goal_difference": 0,
        }

    for match in completed_matches:
        if match.team_one and match.team_one.id in team_stats:
            st = team_stats[match.team_one.id]
            st["matches_played"] += 1
            st["goals_scored"] += match.team_one_score
            st["goals_conceded"] += match.team_two_score
            if match.winner == match.team_one:
                st["wins"] += 1
            else:
                st["losses"] += 1

        if match.team_two and match.team_two.id in team_stats:
            st = team_stats[match.team_two.id]
            st["matches_played"] += 1
            st["goals_scored"] += match.team_two_score
            st["goals_conceded"] += match.team_one_score
            if match.winner == match.team_two:
                st["wins"] += 1
            else:
                st["losses"] += 1

    for st in team_stats.values():
        st["goal_difference"] = st["goals_scored"] - st["goals_conceded"]
        st["points"] = st["wins"] * 3
        st["win_rate"] = (
            round((st["wins"] / st["matches_played"]) * 100, 1)
            if st["matches_played"] > 0
            else 0.0
        )

    team_rankings = sorted(
        team_stats.values(),
        key=lambda x: (x["points"], x["wins"], x["win_rate"], x["goal_difference"]),
        reverse=True,
    )

    recent_matches = list(reversed([m for m in completed_matches if m.team_one and m.team_two][-6:]))

    return {
        "tournament": tournament,
        "registrations": registrations,
        "participant_count": participant_count,
        "registration_percentage": registration_percentage,
        "rounds": rounds,
        "total_matches_count": total_matches_count,
        "completed_matches_count": completed_matches_count,
        "remaining_matches_count": remaining_matches_count,
        "completion_percentage": completion_percentage,
        "total_goals": total_goals,
        "avg_goals": avg_goals,
        "highest_scoring_match": highest_scoring_match,
        "first_completed_match": first_completed_match,
        "last_completed_match": last_completed_match,
        "team_rankings": team_rankings,
        "recent_matches": recent_matches,
    }
