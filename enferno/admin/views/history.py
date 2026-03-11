from __future__ import annotations

from flask import Response
from sqlalchemy import desc

from enferno.admin.models import BulletinHistory, ActorHistory, IncidentHistory, LocationHistory
from enferno.utils.http_response import HTTPResponse
import enferno.utils.typing as t
from . import admin, require_view_history

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
