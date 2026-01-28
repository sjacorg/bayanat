from functools import wraps
from flask import has_request_context
from flask_login import current_user

#  Role based Access Control Decorator for Bulletins / Actors  / Incidents  #


def check_roles(method):
    """
    Decorator to check if the current user has access to the resource. If the
    user does not have access, the restricted_json method is called to return
    a restricted response.
    """

    @wraps(method)
    def _impl(self, *method_args, **method_kwargs):
        method_output = method(self, *method_args, **method_kwargs)
        if current_user:
            if not current_user.can_access(self):
                return self.restricted_json()
        return method_output

    return _impl


def check_relation_roles(method):
    """
    Decorator to check if the current user has access to the related resource.
    If the user does not have access, the restricted_json method is called to
    return a restricted related item in response.
    """

    @wraps(method)
    def _impl(self, *method_args, **method_kwargs):
        method_output = method(self, *method_args, **method_kwargs)
        bulletin = method_output.get("bulletin")
        if bulletin and bulletin.get("restricted"):
            return {"bulletin": bulletin, "restricted": True}

        actor = method_output.get("actor")
        if actor and actor.get("restricted"):
            return {"actor": actor, "restricted": True}

        incident = method_output.get("incident")
        if incident and incident.get("restricted"):
            return {"incident": incident, "restricted": True}
        return method_output

    return _impl


def check_history_access(method):
    """
    Decorator to check if the current user has access to the full history. If the
    user does not have the correct access, the to_dict method will return a shorter
    data history. Also masks usernames if user lacks view_usernames permission.
    """

    def can_view_full():
        if not has_request_context():
            return True  # CLI/Celery - trusted
        return current_user.view_full_history

    def can_view_usernames():
        if not has_request_context():
            return True  # CLI/Celery - trusted
        return current_user.view_usernames or current_user.has_role("Admin")

    def sanitize_data(data):
        if data is None or can_view_usernames():
            return data
        result = data.copy()
        for field in ("assigned_to", "first_peer_reviewer"):
            if result.get(field) and result[field].get("id"):
                mask = f"user-{result[field]['id']}"
                result[field] = {**result[field], "name": mask, "username": mask}
        return result

    @wraps(method)
    def _impl(self, *method_args, **method_kwargs):
        output = method(self, full=can_view_full(), *method_args, **method_kwargs)
        if output.get("data"):
            output["data"] = sanitize_data(output["data"])
        return output

    return _impl
