from datetime import datetime

from geoalchemy2.shape import to_shape

from enferno.utils.logging_utils import get_logger

logger = get_logger()


class FlowmapUtils:
    """Utility class for generating flowmap visualization data from actor life events."""

    @staticmethod
    def generate_from_actors(actors: list) -> dict:
        """
        Generate flowmap data structure from a list of actors.

        Args:
            actors: List of Actor objects with events

        Returns:
            dict: Flowmap data with locations, flows, and metadata
        """
        if not actors:
            logger.info("No actors provided for flowmap generation")
            return FlowmapUtils._empty_flowmap()

        locations_map = {}
        flows_map = {}
        date_range = {"min": None, "max": None}

        for actor in actors:
            FlowmapUtils._process_actor_events(actor, locations_map, flows_map, date_range)

        # Convert actor ID sets to counts and remove internal field
        for loc_data in locations_map.values():
            loc_data["unique_actors"] = len(loc_data.pop("_actor_ids"))

        locations = list(locations_map.values())
        flows = [
            {"origin": origin_id, "dest": dest_id, "events_by_type": events_by_type}
            for (origin_id, dest_id), events_by_type in flows_map.items()
        ]

        metadata = FlowmapUtils._build_metadata(actors, locations, flows, date_range)

        logger.info(
            f"Generated flowmap: {len(actors)} actors, {len(locations)} locations, {len(flows)} flows"
        )

        return {"locations": locations, "flows": flows, "metadata": metadata}

    @staticmethod
    def _empty_flowmap() -> dict:
        """Return empty flowmap structure."""
        return {
            "locations": [],
            "flows": [],
            "metadata": {
                "total_actors": 0,
                "total_locations": 0,
                "total_flows": 0,
                "date_range": None,
            },
        }

    @staticmethod
    def _process_actor_events(
        actor, locations_map: dict, flows_map: dict, date_range: dict
    ) -> None:
        """
        Process all events for a single actor and update location/flow data.

        Args:
            actor: Actor object with events
            locations_map: Dictionary of location_id -> location data
            flows_map: Dictionary of (origin_id, dest_id) -> {event_type: count}
            date_range: Dictionary tracking min/max dates
        """
        events = FlowmapUtils._get_sorted_events(actor)

        if not events:
            return

        prev_location_id = None

        for event in events:
            if not event.location or not event.location.latlng:
                continue

            location = event.location
            location_id = location.id
            event_type = event.eventtype.title if event.eventtype else "Unknown"

            # Add or update location
            if location_id not in locations_map:
                locations_map[location_id] = FlowmapUtils._create_location_data(location)

            loc_data = locations_map[location_id]
            loc_data["events_by_type"][event_type] = (
                loc_data["events_by_type"].get(event_type, 0) + 1
            )
            loc_data["_actor_ids"].add(actor.id)

            # Track date range
            FlowmapUtils._update_date_range(event, date_range)

            # Create flow from previous location to current
            if prev_location_id and prev_location_id != location_id:
                flow_key = (prev_location_id, location_id)
                if flow_key not in flows_map:
                    flows_map[flow_key] = {}
                flows_map[flow_key][event_type] = flows_map[flow_key].get(event_type, 0) + 1

            prev_location_id = location_id

    @staticmethod
    def _get_sorted_events(actor) -> list:
        """
        Get chronologically sorted events for an actor.

        Args:
            actor: Actor object with events

        Returns:
            list: Events sorted by from_date, then to_date
        """
        return sorted(
            actor.events,
            key=lambda e: (
                e.from_date or datetime.max,
                e.to_date or datetime.max,
            ),
        )

    @staticmethod
    def _create_location_data(location) -> dict:
        """
        Create location data dictionary from Location object.

        Args:
            location: Location object with latlng

        Returns:
            dict: Location data with id, name, lat, lon, events_by_type
        """
        shape = to_shape(location.latlng)
        return {
            "id": location.id,
            "name": location.full_location or location.title or f"Location {location.id}",
            "lat": shape.y,
            "lon": shape.x,
            "events_by_type": {},
            "_actor_ids": set(),
        }

    @staticmethod
    def _update_date_range(event, date_range: dict) -> None:
        """
        Update date range tracking with event dates.

        Args:
            event: Event object with from_date
            date_range: Dictionary with 'min' and 'max' keys
        """
        if not event.from_date:
            return

        if date_range["min"] is None or event.from_date < date_range["min"]:
            date_range["min"] = event.from_date

        if date_range["max"] is None or event.from_date > date_range["max"]:
            date_range["max"] = event.from_date

    @staticmethod
    def _build_metadata(actors: list, locations: list, flows: list, date_range: dict) -> dict:
        """
        Build metadata summary for the flowmap.

        Args:
            actors: List of Actor objects
            locations: List of location data dictionaries
            flows: List of flow data dictionaries
            date_range: Dictionary with 'min' and 'max' date keys

        Returns:
            dict: Metadata summary
        """
        date_range_data = None
        if date_range["min"] or date_range["max"]:
            date_range_data = {
                "start": date_range["min"].isoformat() if date_range["min"] else None,
                "end": date_range["max"].isoformat() if date_range["max"] else None,
            }

        return {
            "total_actors": len(actors),
            "total_locations": len(locations),
            "total_flows": len(flows),
            "date_range": date_range_data,
        }
