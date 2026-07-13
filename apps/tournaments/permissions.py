from django.core.exceptions import PermissionDenied


def can_manage_tournament(user, tournament):
    """
    Returns True if the user can manage the tournament.
    """

    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    return tournament.organizer == user


def require_tournament_manager(user, tournament):
    """
    Raises 403 if the user cannot manage the tournament.
    """

    if not can_manage_tournament(user, tournament):
        raise PermissionDenied