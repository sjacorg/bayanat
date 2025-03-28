from functools import wraps
from flask import has_app_context, has_request_context
from flask_login import current_user

#  Role based Access Control Decorator for Bulletins / Actors  / Incidents  #


def check_roles(method):
    """
    Decorator to check if the current user has access to the resource. If the
    user does not have access, the restricted_json method is called to return
    a restricted response. Role checking is skipped when there's no request context
    (e.g. during ETL operations).
    """

    @wraps(method)
    def _impl(self, *method_args, **method_kwargs):
        method_output = method(self, *method_args, **method_kwargs)
        if has_request_context() and current_user:
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
    Decorator to check if the current user has access to the fulll history. If the
    user does not have the correct access, the to_dict method will return a shorter
    data histroy.
    """

    def can_access():
        if has_request_context() and has_app_context():
            return True if current_user.view_full_history else False
        return True

    @wraps(method)
    def _impl(self, *method_args, **method_kwargs):
        return method(self, full=can_access(), *method_args, **method_kwargs)

    return _impl
