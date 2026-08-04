from __future__ import annotations

from flask import Response
from flask_security.decorators import current_user
from sqlalchemy import desc

from enferno.admin.models import (
    Activity,
    Actor,
    ActorHistory,
    Bulletin,
    BulletinHistory,
    Incident,
    IncidentHistory,
    LocationHistory,
)
from enferno.extensions import db
from enferno.utils.http_response import HTTPResponse
import enferno.utils.typing as t
from . import admin, require_view_history


def _deny_history(parent_label: str, parent_id: int) -> Response:
    """Log a denied history view and return a forbidden response."""
    Activity.create(
        current_user,
        Activity.ACTION_VIEW,
        Activity.STATUS_DENIED,
        {"id": parent_id},
        parent_label,
        details=f"Unauthorized attempt to view history of restricted {parent_label} {parent_id}.",
    )
    return HTTPResponse.forbidden("Restricted Access")


# Bulletin History Helpers


@admin.route("/api/bulletinhistory/<int:bulletinid>")
@require_view_history
def api_bulletinhistory(bulletinid: t.id) -> Response:
    """
    Endpoint to get revision history of a bulletin.

    Args:
        - bulletinid: id of the bulletin item.

    Returns:
        - json feed of item's history / error.
    """
    bulletin = db.session.get(Bulletin, bulletinid)
    if not bulletin:
        return HTTPResponse.not_found("Bulletin not found")
    if not current_user.can_access(bulletin):
        return _deny_history("bulletin", bulletinid)

    result = (
        BulletinHistory.query.filter_by(bulletin_id=bulletinid)
        .order_by(desc(BulletinHistory.created_at))
        .all()
    )

    # For standardization
    response = {"items": [item.to_dict() for item in result]}
    return HTTPResponse.success(data=response)


# Actor History Helpers


@admin.route("/api/actorhistory/<int:actorid>")
@require_view_history
def api_actorhistory(actorid: t.id) -> Response:
    """
    Endpoint to get revision history of an actor.

    Args:
        - actorid: id of the actor item.

    Returns:
        - json feed of item's history / error.
    """
    actor = db.session.get(Actor, actorid)
    if not actor:
        return HTTPResponse.not_found("Actor not found")
    if not current_user.can_access(actor):
        return _deny_history("actor", actorid)

    result = (
        ActorHistory.query.filter_by(actor_id=actorid).order_by(desc(ActorHistory.created_at)).all()
    )
    # For standardization
    response = {"items": [item.to_dict() for item in result]}
    return HTTPResponse.success(data=response)


# Incident History Helpers


@admin.route("/api/incidenthistory/<int:incidentid>")
@require_view_history
def api_incidenthistory(incidentid: t.id) -> Response:
    """
    Endpoint to get revision history of an incident item.

    Args:
        - incidentid: id of the incident item.

    Returns:
        - json feed of item's history / error.
    """
    incident = db.session.get(Incident, incidentid)
    if not incident:
        return HTTPResponse.not_found("Incident not found")
    if not current_user.can_access(incident):
        return _deny_history("incident", incidentid)

    result = (
        IncidentHistory.query.filter_by(incident_id=incidentid)
        .order_by(desc(IncidentHistory.created_at))
        .all()
    )
    # For standardization
    response = {"items": [item.to_dict() for item in result]}
    return HTTPResponse.success(data=response)


# Location History Helpers


@admin.route("/api/locationhistory/<int:locationid>")
@require_view_history
def api_locationhistory(locationid: t.id) -> Response:
    """
    Endpoint to get revision history of a location.

    Args:
        - locationid: id of the location item.

    Returns:
        - json feed of item's history / error.
    """
    result = (
        LocationHistory.query.filter_by(location_id=locationid)
        .order_by(desc(LocationHistory.created_at))
        .all()
    )
    # For standardization
    response = {"items": [item.to_dict() for item in result]}
    return HTTPResponse.success(data=response)
