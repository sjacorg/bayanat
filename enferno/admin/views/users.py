from __future__ import annotations

from typing import Any
from uuid import uuid4

from flask import Response, request, current_app, session
from flask.templating import render_template
from flask_security import logout_user
from flask_security.decorators import auth_required, current_user, roles_accepted, roles_required
from flask_security.twofactor import tf_disable
from sqlalchemy import or_

from enferno.admin.constants import Constants
from enferno.admin.models import Activity
from enferno.admin.models.Notification import Notification
from enferno.admin.validation.models import (
    UserRequestModel,
    UserNameCheckValidationModel,
    UserPasswordCheckValidationModel,
    UserForceResetRequestModel,
    RoleRequestModel,
)
from enferno.extensions import db
from enferno.user.models import User, Role, Session
from enferno.utils.http_response import HTTPResponse
from enferno.utils.logging_utils import get_logger
from enferno.utils.validation_utils import validate_with
import enferno.utils.typing as t
from . import admin, PER_PAGE

logger = get_logger()

# user management routes


@admin.route("/api/users/")
@roles_accepted("Admin", "Mod")
def api_users() -> Response:
    """
    API endpoint to feed users data in json format , supports paging and search.

    Returns:
        - json feed of users / error.
    """
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)
    q = request.args.get("q")
    query = []
    if q is not None:
        query.append(User.name.ilike("%" + q + "%"))
    result = (
        User.query.filter(*query)
        .order_by(User.username)
        .paginate(page=page, per_page=per_page, count=True)
    )

    response = {
        "items": [
            item.to_dict() if current_user.has_role("Admin") else item.to_compact()
            for item in result.items
        ],
        "perPage": per_page,
        "total": result.total,
    }

    return HTTPResponse.success(data=response)


@admin.get("/users/", defaults={"id": None})
@admin.get("/users/<int:id>")
@auth_required(within=15, grace=0)
@roles_required("Admin")
def users(id) -> str:
    """
    Endpoint to render the users backend page.

    Returns:
        - html page of the users backend.
    """
    return render_template("admin/users.html")


@admin.get("/api/user/<int:id>")
@roles_required("Admin")
def api_user_get(id) -> Response:
    """
    Endpoint to get a user
    :param id: id of the user
    :return: user data in json format + success or error in case of failure
    """
    user = User.query.get(id)
    if not user:
        return HTTPResponse.not_found("User not found")
    else:
        return HTTPResponse.success(data=user.to_dict())


@admin.get("/api/user/<int:id>/sessions")
@roles_required("Admin")
def api_user_sessions(id: int) -> Any:
    """
    Retrieve paginated session data for a specific user.

    Args:
        id (int): The ID of the user whose sessions are to be retrieved.

    Returns:
        Any: A dictionary with session details and pagination info, or an error message and HTTP status code.
    """

    session_redis = current_app.config["SESSION_REDIS"]
    session_interface = current_app.session_interface
    per_page = request.args.get("per_page", PER_PAGE, int)
    page = request.args.get("page", 1, int)

    try:
        # Fetch the user to ensure they exist and to collect their session tokens
        user = User.query.get(id)
        if not user:
            return HTTPResponse.not_found("User not found")
        sessions_paginated = (
            Session.query.filter(Session.user_id == id).order_by(Session.created_at.desc())
        ).paginate(page=page, per_page=per_page, error_out=False)

        # Collect tokens from user's sessions to filter Redis keys
        user_session_tokens = {s.session_token for s in sessions_paginated.items}

        user_redis_keys = [f"session:{token}" for token in user_session_tokens if token]

        # Retrieve and decode session details from Redis, storing in a dictionary
        redis_sessions_details = {}
        for key in user_redis_keys:
            data = session_redis.get(key)
            if data:
                token = key.split(":")[1]
                session_data = session_interface.serializer.decode(data)
                # hide session details from the response
                redis_sessions_details[token] = {"_fresh": session_data.get("_fresh")}

        # Prepare the session data for response including the details
        sessions_data = []

        for s in sessions_paginated.items:
            session_info = s.to_dict()
            if s.session_token in redis_sessions_details:
                session_info["details"] = redis_sessions_details[s.session_token]
            session_info["active"] = s.session_token == session.sid
            sessions_data.append(session_info)

        # Determine if there are more items left
        more = sessions_paginated.has_next

        return HTTPResponse.success(data={"items": sessions_data, "more": more})

    except Exception as e:
        logger.error(f"Failed to get sessions: {str(e)}", exc_info=True)
        return HTTPResponse.error("Server error", status=500)


@admin.delete("/api/session/logout")
@roles_required("Admin")
def logout_session() -> Response:
    """
    Handle session logout by session id (admin only).

    Returns appropriate messages based on the success or failure of the logout operation.
    """

    # get the sessid from the JSON payload
    sessid = request.json.get("sessid", None)
    if not sessid:
        return HTTPResponse.error("Invalid request. Please provide a session ID.")
    try:
        # Query the database to get the session token using the sessid
        session_ = Session.query.get(sessid)

        if not session_:
            return HTTPResponse.not_found(f"Session ID {sessid} not found.")

        token = session_.session_token

        if token == session.sid:
            logout_user()
            # Use a custom JSON response with a specific field to signal a redirect to the front-end
            return HTTPResponse.success(data={"logout": "successful", "redirect": True})

        rds = current_app.config["SESSION_REDIS"]
        session_key = f"session:{token}"

        # Check if the session key exists in Redis
        if rds.exists(session_key):
            # Delete the session key from Redis
            rds.delete(session_key)
            return HTTPResponse.success(message=f"Session {sessid} logged out successfully.")
        else:
            return HTTPResponse.not_found(f"Session {sessid} not found in Redis.")

    except Exception as e:
        logger.error(f"Error while logging out session: {str(e)}", exc_info=True)
        return HTTPResponse.error("Error while logging out session", status=500)


@admin.delete("/api/user/<int:user_id>/sessions/logout")
@roles_required("Admin")
def logout_all_sessions(user_id: int) -> Any:
    """
    Log out all sessions for a given user.

    Args:
        user_id (int): The ID of the user whose sessions will be logged out.

    Returns:
        Tuple[Union[str, dict], int]: A response message and HTTP status code.
    """
    # Fetch the user to ensure they exist
    user = User.query.get(user_id)
    if not user:
        return HTTPResponse.not_found("User not found")

    rds = current_app.config["SESSION_REDIS"]
    errors = []
    current_session_logout_needed = False

    # Iterate over user's sessions and delete them from Redis, except the current session
    for s in user.sessions:
        if s.session_token == session.sid:
            current_session_logout_needed = True
            continue

        try:
            session_key = f"session:{s.session_token}"
            if rds.exists(session_key):
                rds.delete(session_key)
        except Exception as e:
            logger.error(f"Failed to delete session {s.id}: {str(e)}", exc_info=True)
            errors.append(f"Failed to delete session {s.id}")

    # Logout current session last if needed
    if current_session_logout_needed:
        logout_user()

    # Build response
    if errors:
        return HTTPResponse.error("Error while logging out sessions", status=500, errors=errors)
    return HTTPResponse.success(message=f"All sessions for user {user_id} logged out successfully")


@admin.delete("/api/user/revoke_2fa")
@roles_required("Admin")
def revoke_2fa() -> Response:
    """
    Revoke 2FA for a specified user.

    Returns:
        Tuple[str, int]: A success message and HTTP status code.
    """
    user_id: int = request.args.get("user_id", default=None, type=int)

    if not user_id:
        return HTTPResponse.error("User ID is required")

    user = User.query.get(user_id)
    if not user:
        return HTTPResponse.not_found("User not found")

    tf_disable(user)
    # also clear all webauthn credentials
    for cred in user.webauthn:
        db.session.delete(cred)
    user.save()

    return HTTPResponse.success(message=f"2FA revoked for user {user_id} successfully")


@admin.post("/api/user/")
@roles_required("Admin")
@validate_with(UserRequestModel)
def api_user_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create a user item.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    # validate existing
    u = validated_data.get("item")
    username = u.get("username")
    if email := u.get("email"):
        query = User.query.filter(or_(User.username == username, User.email == email))
    else:
        query = User.query.filter(User.username == username)

    existing_user = query.first()

    if existing_user:
        if existing_user.username == username:
            return "Error, username already exists", 409
        elif existing_user.email == email:
            return "Error, email already exists", 409
    user = User()
    user.fs_uniquifier = uuid4().hex
    user.from_json(u)
    result = user.save()
    if result:
        # Record activity
        Activity.create(
            current_user, Activity.ACTION_CREATE, Activity.STATUS_SUCCESS, user.to_mini(), "user"
        )
        # Notify admins
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.NEW_USER,
            "New User Created",
            f"User {username} has been created by {current_user.username} successfully.",
        )
        return HTTPResponse.created(
            message=f"User {username} has been created successfully",
            data={"item": user.to_dict()},
        )
    else:
        return HTTPResponse.error("Error creating user", status=500)


@admin.post("/api/checkuser/")
@roles_required("Admin")
@validate_with(UserNameCheckValidationModel)
def api_user_check(
    validated_data: dict,
) -> Response:
    """
    API endpoint to validate a username.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    data = validated_data.get("item")
    if not data:
        return HTTPResponse.error("Please select a username", status=400)

    # Check if username already exists
    u = User.query.filter(User.username == data).first()
    if u:
        return "Username already exists", 409
    else:
        return HTTPResponse.success(message="Username ok")


@admin.put("/api/user/")
@roles_required("Admin")
@validate_with(UserRequestModel)
def api_user_update(
    validated_data: dict,
) -> Response:
    """
    Endpoint to update a user.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    item = validated_data.get("item")
    user = User.query.get(item.get("id"))
    if user is not None:
        u = validated_data.get("item")
        username = u.get("username")

        # Check if username or email already exists (excluding current user)
        if email := u.get("email"):
            query = User.query.filter(
                or_(User.username == username, User.email == email), User.id != user.id
            )
        else:
            query = User.query.filter(User.username == username, User.id != user.id)

        existing_user = query.first()

        if existing_user:
            if existing_user.username == username:
                return "Error, username already exists", 409
            elif existing_user.email == email:
                return "Error, email already exists", 409

        user = user.from_json(u)
        if user.save():
            # Record activity
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_SUCCESS,
                user.to_mini(),
                "user",
            )
            # Notify admins
            Notification.send_admin_notification_for_event(
                Constants.NotificationEvent.UPDATE_USER,
                "User Updated",
                f"User {user.username} has been updated by {current_user.username} successfully.",
            )
            return HTTPResponse.success(message=f"Saved User {user.id} {user.name}")
        else:
            return HTTPResponse.error(f"Error saving User {user.id} {user.name}", status=500)
    else:
        return HTTPResponse.not_found("User not found")


@admin.post("/api/password/")
@validate_with(UserPasswordCheckValidationModel)
def api_check_password(
    validated_data: dict,
) -> Response:
    """
    API Endpoint to validate a password and check its strength.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    # Password is validated in the UserPasswordCheckValidationModel
    # If the request reached here, the password is valid
    return "Password is ok", 200


@admin.post("/api/user/force-reset")
@roles_required("Admin")
@validate_with(UserForceResetRequestModel)
def api_user_force_reset(validated_data: dict) -> Response:
    """
    Endpoint to force a password reset for a user.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    item = validated_data.get("item")
    if not item or not (id := item.get("id")):
        return HTTPResponse.error("Bad Request")
    user = User.query.get(id)
    if not user:
        return HTTPResponse.not_found("User not found")
    if reset_key := user.security_reset_key:
        message = f"Forced password reset already requested: {reset_key}"
        return HTTPResponse.error(message)
    user.set_security_reset_key()
    message = f"Forced password reset has been set for user {user.username}"
    return HTTPResponse.success(message=message)


@admin.post("/api/user/force-reset-all")
@roles_required("Admin")
def api_user_force_reset_all() -> Response:
    """
    sets a redis flag to force password reset for all users.

    Returns:
        - success response after setting all redis flags (if not already set)
    """
    for user in User.query.all():
        # check if user already has a password reset flag
        if not user.security_reset_key:
            user.set_security_reset_key()
    return HTTPResponse.success(message="Forced password reset has been set for all users")


@admin.delete("/api/user/<int:id>")
@roles_required("Admin")
def api_user_delete(
    id: t.id,
) -> Response:
    """
    Endpoint to delete a user.

    Args:
        - id: id of the user to be deleted.

    Returns:
        - success/error string based on the operation result.
    """
    user = User.query.get(id)
    if user is None:
        return HTTPResponse.not_found("User not found")

    if user.active:
        return HTTPResponse.forbidden("User is active, make inactive before deleting")

    if user.delete():
        # Record activity
        Activity.create(
            current_user, Activity.ACTION_DELETE, Activity.STATUS_SUCCESS, user.to_mini(), "user"
        )
        # Notify admins
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.ITEM_DELETED,
            "User Deleted",
            f"User {user.username} has been deleted by {current_user.username} successfully.",
        )
        return HTTPResponse.success(message="Deleted")
    else:
        return HTTPResponse.error("Error deleting User", status=500)


# Roles routes
@admin.route("/roles/")
@auth_required(within=15, grace=0)
@roles_required("Admin")
def roles() -> str:
    """
    Endpoint to redner roles backend page.

    Returns:
        - html page of the roles backend.
    """
    return render_template("admin/roles.html")


@admin.get("/api/roles/")
@roles_required("Admin")
def api_roles() -> Response:
    """
    API endpoint to feed roles items in josn format - supports paging and search.

    Returns:
        - json feed of roles / error.
    """
    query = []
    q = request.args.get("q", None)
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)
    if q is not None:
        query.append(Role.name.ilike("%" + q + "%"))
    result = (
        Role.query.filter(*query)
        .order_by(Role.id)
        .paginate(page=page, per_page=per_page, count=True)
    )
    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return HTTPResponse.success(data=response)


@admin.post("/api/role/")
@roles_required("Admin")
@validate_with(RoleRequestModel)
def api_role_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create a role item.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    role = Role()
    created = role.from_json(validated_data["item"])
    if created.save():
        # Record activity
        Activity.create(
            current_user, Activity.ACTION_CREATE, Activity.STATUS_SUCCESS, role.to_mini(), "role"
        )
        # Notify admins
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.NEW_GROUP,
            "New Group Created",
            f"Group {role.name} has been created by {current_user.username} successfully.",
        )
        return HTTPResponse.created(message="Created", data={"item": role.to_dict()})

    else:
        return HTTPResponse.error("Save Failed", status=500)


@admin.put("/api/role/<int:id>")
@roles_required("Admin")
@validate_with(RoleRequestModel)
def api_role_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update a role item.

    Args:
        - id: id of the role to be updated.
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    role = Role.query.get(id)
    if role is None:
        return HTTPResponse.not_found("Role not found")

    if role.name in ["Admin", "Mod", "DA"]:
        return HTTPResponse.forbidden("Cannot edit System Roles")

    role = role.from_json(validated_data["item"])
    role.save()
    # Record activity
    Activity.create(
        current_user, Activity.ACTION_UPDATE, Activity.STATUS_SUCCESS, role.to_mini(), "role"
    )
    return HTTPResponse.success(message=f"Role {id} Updated")


@admin.delete("/api/role/<int:id>")
@roles_required("Admin")
def api_role_delete(
    id: t.id,
) -> Response:
    """
    Endpoint to delete a role item.

    Args:
        - id: id of the role to be deleted.

    Returns:
        - success/error string based on the operation result.
    """
    role = Role.query.get(id)

    if role is None:
        return HTTPResponse.not_found("Role not found")

    # forbid deleting system roles
    if role.name in ["Admin", "Mod", "DA"]:
        return HTTPResponse.forbidden("Cannot delete System Roles")
    # forbid delete roles assigned to restricted items
    if role.bulletins.first() or role.actors.first() or role.incidents.first():
        return HTTPResponse.forbidden("Role assigned to restricted items")

    if role.delete():
        # Record activity
        Activity.create(
            current_user, Activity.ACTION_DELETE, Activity.STATUS_SUCCESS, role.to_mini(), "role"
        )
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.ITEM_DELETED,
            "Role Deleted",
            f"Role {role.name} has been deleted by {current_user.username} successfully.",
        )
        return HTTPResponse.success(message="Deleted")
    else:
        return HTTPResponse.error("Error deleting Role", status=500)


@admin.post("/api/role/import/")
@roles_required("Admin")
def api_role_import() -> Response:
    """
    Endpoint to import role items from a CSV file.

    Returns:
        - success/error string based on the operation result.
    """
    if "csv" in request.files:
        Role.import_csv(request.files.get("csv"))
        return HTTPResponse.success(message="Success")
    else:
        return HTTPResponse.error("Error")
