from functools import wraps

from django.core.exceptions import PermissionDenied


def role_required(required_role):
    """
    Allows access only to users having the specified role.
    """

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            if request.user.role != required_role:
                raise PermissionDenied

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def admin_required(view_func):
    return role_required("ADMIN")(view_func)


def captain_required(view_func):
    return role_required("CAPTAIN")(view_func)


def player_required(view_func):
    return role_required("PLAYER")(view_func)