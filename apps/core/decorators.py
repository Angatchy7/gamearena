from functools import wraps

from django.core.exceptions import PermissionDenied

from apps.accounts.models import User


def admin_required(view_func):
    """
    Allows access only to website administrators.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if request.user.role != User.Role.ADMIN:
            raise PermissionDenied

        return view_func(request, *args, **kwargs)

    return wrapper