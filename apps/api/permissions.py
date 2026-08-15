from rest_framework import permissions


class IsTeamManager(permissions.BasePermission):
    """
    Custom permission allowing access only to the team's manager.
    Expects the view object to have a team or get_team method, or checks obj.manager / obj.team.manager.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False

        if hasattr(obj, "manager"):
            return obj.manager == request.user
        if hasattr(obj, "team") and hasattr(obj.team, "manager"):
            return obj.team.manager == request.user

        return False


class IsTournamentOrganizer(permissions.BasePermission):
    """
    Custom permission allowing write access only to the tournament organizer.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False

        if hasattr(obj, "organizer"):
            return obj.organizer == request.user
        if hasattr(obj, "round") and hasattr(obj.round, "tournament"):
            return obj.round.tournament.organizer == request.user

        return False
