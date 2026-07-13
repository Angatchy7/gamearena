from django.db import transaction
from django.utils import timezone

from .models import Tournament


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

    tournament.status = Tournament.Status.LIVE

    tournament.save(update_fields=["status"])


@transaction.atomic
def cancel_tournament(*, tournament):

    tournament.status = Tournament.Status.CANCELLED

    tournament.save(update_fields=["status"])