from __future__ import annotations

import os
from functools import wraps

from flask import Blueprint, g, request
from flask_security.decorators import auth_required, current_user

from enferno.admin.models import Activity
from enferno.user.models import User
from enferno.utils.http_response import HTTPResponse
from enferno.utils.logging_utils import get_logger

root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
admin = Blueprint(
    "admin",
    __name__,
    template_folder=os.path.join(root, "templates"),
    static_folder=os.path.join(root, "static"),
    url_prefix="/admin",
)

# default global items per page
PER_PAGE = 30
REL_PER_PAGE = 5

logger = get_logger()


# History access decorators


def require_view_history(f):
    """
    Decorator to ensure the user has the required permissions to view history.
    """

    @wraps(f)
    # Ensure the user is logged in before checking permissions
    @auth_required("session")
    def decorated_function(*args, **kwargs):
        # Check if user has the required view history permissions
        if not (
            current_user.has_role("Admin")
            or current_user.view_simple_history
            or current_user.view_full_history
        ):
            return HTTPResponse.forbidden()
        return f(*args, **kwargs)

    return decorated_function


def can_assign_roles(func):
    """
    Decorator to ensure the user has the required permissions to assign roles.
    """

    @wraps(func)
    def decorated_function(*args, **kwargs):
        roles = request.json.get("item", {}).get("roles", [])
        if roles:
            if not has_role_assignment_permission(roles):
                Activity.create(
                    current_user,
                    Activity.ACTION_CREATE,
                    Activity.STATUS_DENIED,
                    request.json,
                    "bulletin",
                    details="Unauthorized attempt to assign roles.",
                )
                return HTTPResponse.forbidden("Unauthorized")
        return func(*args, **kwargs)

    return decorated_function


def has_role_assignment_permission(roles: list) -> bool:
    """
    Function to check if the current user has the required permissions to assign roles.

    Args:
        - roles: List of role ids to assign.

    Returns:
        - True if the user has the required permissions, False otherwise.
    """
    # admins can assign any roles
    if not current_user.has_role("Admin"):
        # non-admins can only assign their roles
        from flask import current_app

        user_roles = {role.id for role in current_user.roles}
        requested_roles = set([role.get("id") for role in roles])
        if not requested_roles.issubset(user_roles) or not current_app.config.get(
            "AC_USERS_CAN_RESTRICT_NEW"
        ):
            return False

    return True


@admin.before_request
@auth_required("session")
def before_request() -> None:
    """
    Attaches the user object to all requests
    and a version number that is used to clear the static files cache globally.
    """
    g.user = current_user
    g.version = "5"


@admin.app_context_processor
def ctx() -> dict:
    """
    passes all users to the application, based on the current user's permissions.

    Returns:
        - dict of users
    """
    users = User.query.order_by(User.username).all()
    if current_user and current_user.is_authenticated:
        users = [u.to_compact() for u in users]
        return {"users": users}
    return {}


# Import all sub-modules to register their routes
from . import labels  # noqa: E402, F401
from . import eventtypes  # noqa: E402, F401
from . import violations  # noqa: E402, F401
from . import sources  # noqa: E402, F401
from . import locations  # noqa: E402, F401
from . import reference_data  # noqa: E402, F401
from . import relationship_infos  # noqa: E402, F401
from . import bulletins  # noqa: E402, F401
from . import media  # noqa: E402, F401
from . import actors  # noqa: E402, F401
from . import history  # noqa: E402, F401
from . import users  # noqa: E402, F401, F811
from . import incidents  # noqa: E402, F401
from . import activity  # noqa: E402, F401
from . import system  # noqa: E402, F401
from . import logs  # noqa: E402, F401
from . import notifications  # noqa: E402, F401
from . import dynamic_fields  # noqa: E402, F401
from . import flowmap  # noqa: E402, F401
