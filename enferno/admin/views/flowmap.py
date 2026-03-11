from __future__ import annotations

import json
from datetime import datetime

from flask import Response
from flask_security.decorators import current_user
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from enferno.admin.models import Actor, Event, Eventtype
from enferno.admin.models.tables import actor_events
from enferno.admin.validation.models import (
    FlowmapActorsForLocationsModel,
    FlowmapVisualizeRequestModel,
)
from enferno.extensions import db, rds
from enferno.tasks import generate_actor_flowmap
from enferno.utils.http_response import HTTPResponse
from enferno.utils.search_utils import SearchUtils
from enferno.utils.validation_utils import validate_with
from . import admin


@admin.post("/api/flowmap/visualize")
@validate_with(FlowmapVisualizeRequestModel)
def flowmap_visualize(validated_data: dict) -> Response:
    """Generate actor flowmap visualization."""
    task_id = generate_actor_flowmap.delay(validated_data["q"], current_user.id)
    return HTTPResponse.success(data={"task_id": task_id.id})


@admin.get("/api/flowmap/data")
def get_flowmap_data() -> Response:
    """Retrieve flowmap data from Redis."""
    data_key = f"user{current_user.id}:flowmap:data"
    flowmap_data = rds.get(data_key)

    if not flowmap_data:
        return HTTPResponse.not_found("Flowmap data not found")

    return HTTPResponse.success(data=json.loads(flowmap_data))


@admin.get("/api/flowmap/status")
def check_flowmap_status() -> Response:
    """Get flowmap task status."""
    user_id = current_user.id
    status = rds.get(f"user{user_id}:flowmap:status")

    if not status:
        return HTTPResponse.not_found("Flowmap status not found")

    response_data = {"status": status.decode("utf-8")}

    if response_data["status"] == "error":
        error_msg = rds.get(f"user{user_id}:flowmap:error")
        if error_msg:
            response_data["error"] = error_msg.decode("utf-8")

    return HTTPResponse.success(data=response_data)


@admin.post("/api/flowmap/actors-for-locations")
@validate_with(FlowmapActorsForLocationsModel)
def flowmap_actors_for_locations(validated_data: dict) -> Response:
    """
    Return actors associated with specific locations on the flowmap.

    Modes:
    1. Node click:  { location_ids: [...], q: [...] }
    2. Flow click:  { origin_ids: [...], dest_ids: [...], q: [...] }

    Optional: event_types: ["Arrest", "Detained/Abducted"] -> filter by event type name
    """
    q = validated_data.get("q", [{}])
    origin_ids = validated_data.get("origin_ids")
    dest_ids = validated_data.get("dest_ids")
    location_ids = validated_data.get("location_ids")
    event_types = validated_data.get("event_types")

    et_filter = set(event_types) if event_types else None

    # Get scoped actor IDs as a subquery
    search_util = SearchUtils(q, cls="actor")
    scoped_stmt = search_util.get_query()
    scoped_ids_subq = scoped_stmt.with_only_columns(Actor.id).subquery()

    # Determine which location IDs matter
    if origin_ids and dest_ids:
        all_location_ids = list(set(origin_ids) | set(dest_ids))
    else:
        all_location_ids = list(set(location_ids))

    # SQL-level filter: only actors with events at relevant locations
    candidate_ids_q = (
        select(Actor.id)
        .join(actor_events, actor_events.c.actor_id == Actor.id)
        .join(Event, actor_events.c.event_id == Event.id)
        .where(
            Actor.id.in_(select(scoped_ids_subq.c.id)),
            Event.location_id.in_(all_location_ids),
        )
    )

    # For node mode, also filter by event type at SQL level
    is_flow_mode = bool(origin_ids and dest_ids)
    if et_filter and not is_flow_mode:
        candidate_ids_q = candidate_ids_q.join(Eventtype, Event.eventtype_id == Eventtype.id).where(
            Eventtype.title.in_(et_filter)
        )

    candidate_ids_q = candidate_ids_q.distinct()

    # Load only candidate actors with eagerly loaded events
    actors = (
        db.session.execute(
            select(Actor)
            .where(Actor.id.in_(candidate_ids_q))
            .options(
                joinedload(Actor.events).joinedload(Event.location),
                joinedload(Actor.events).joinedload(Event.eventtype),
            )
        )
        .scalars()
        .unique()
        .all()
    )

    def serialize_event(event):
        if not event:
            return None
        return {
            "id": event.id,
            "type": event.eventtype.title if event.eventtype else None,
            "location": event.location.title if event.location else None,
            "location_id": event.location.id if event.location else None,
            "from_date": event.from_date.isoformat() if event.from_date else None,
            "to_date": event.to_date.isoformat() if event.to_date else None,
        }

    def sort_events(events):
        return sorted(
            events,
            key=lambda e: (
                e.from_date or datetime.max,
                e.to_date or datetime.max,
            ),
        )

    # FLOW MODE (directional)
    if origin_ids and dest_ids:
        origin_set = set(origin_ids)
        dest_set = set(dest_ids)
        results = []

        for actor in actors:
            events = sort_events(actor.events)
            origin_event = None
            dest_event = None

            for event in events:
                if not event.location:
                    continue
                loc_id = event.location.id
                if loc_id in origin_set and not origin_event:
                    origin_event = event
                elif loc_id in dest_set and origin_event:
                    dest_event = event
                    break

            if origin_event and dest_event:
                payload = actor.to_compact()
                payload["origin_event"] = serialize_event(origin_event)
                payload["dest_event"] = serialize_event(dest_event)
                results.append(payload)

        return HTTPResponse.success(data={"items": results, "total": len(results)})

    # NODE MODE
    else:
        location_set = set(location_ids)
        results = []

        for actor in actors:
            events = sort_events(actor.events)

            for i, event in enumerate(events):
                if not event.location:
                    continue
                if event.location.id not in location_set:
                    continue
                if et_filter:
                    et_title = event.eventtype.title if event.eventtype else None
                    if et_title not in et_filter:
                        continue

                payload = actor.to_compact()
                prev_event = events[i - 1] if i > 0 else None
                next_event = events[i + 1] if i < len(events) - 1 else None
                payload["prev_event"] = serialize_event(prev_event)
                payload["current_event"] = serialize_event(event)
                payload["next_event"] = serialize_event(next_event)
                results.append(payload)
                break

        return HTTPResponse.success(data={"items": results, "total": len(results)})
