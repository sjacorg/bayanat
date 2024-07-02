import json

from sqlalchemy import or_

from enferno.admin.models import (
    Btob,
    Bulletin,
    Atob,
    Itob,
    Actor,
    Incident,
    Atoa,
    Itoa,
    Itoi,
    bulletin_locations,
    Location,
    bulletin_events,
    Event,
    actor_events,
    incident_locations,
    incident_events,
)
from enferno.extensions import db

class_mapping = {"bulletin": Bulletin, "actor": Actor, "incident": Incident}


def add_node(node, node_list):
    if node not in node_list:
        node_list.append(node)


def add_relation(relation, relations_list):
    if relation not in relations_list:
        relations_list.append(relation)


def create_node(id, title, model):
    return {
        "id": f"{model.__name__}{id}",
        "_id": id,
        "title": title,
        "color": model.COLOR,
        "type": model.__name__,
        "collapsed": True,
        "childLinks": [],
    }


class GraphUtils:
    @staticmethod
    def get_graph_json(entity_type, entity_id) -> str:
        entity_class = class_mapping.get(entity_type)
        if not entity_class:
            raise ValueError("Invalid entity type")

        # Logic to handle different entity types and their relationships
        if entity_type == "bulletin":
            return GraphUtils.get_bulletin_graph(entity_id)
        elif entity_type == "actor":
            return GraphUtils.get_actor_graph(entity_id)
        elif entity_type == "incident":
            return GraphUtils.get_incident_graph(entity_id)
        else:
            raise ValueError("Unsupported entity type")

    @staticmethod
    def get_bulletin_graph(bulletin_id):
        nodes = []
        relations = []

        # Bulletins
        btob_relations = Btob.query.filter(
            or_(Btob.bulletin_id == bulletin_id, Btob.related_bulletin_id == bulletin_id)
        ).all()

        for r in btob_relations:
            source_bulletin = create_node(r.bulletin_from.id, r.bulletin_from.title, Bulletin)
            target_bulletin = create_node(r.bulletin_to.id, r.bulletin_to.title, Bulletin)

            add_node(source_bulletin, nodes)
            add_node(target_bulletin, nodes)

            add_relation(
                {
                    "source": source_bulletin["id"],
                    "target": target_bulletin["id"],
                    "type": r.related_as or "",
                },
                relations,
            )

        # add bulletin node
        bulletin_node = create_node(bulletin_id, Bulletin.query.get(bulletin_id).title, Bulletin)
        add_node(bulletin_node, nodes)

        # Actors
        atob_relations = Atob.query.filter(Atob.bulletin_id == bulletin_id).all()
        for r in atob_relations:
            actor = create_node(r.actor.id, r.actor.name, Actor)
            add_node(actor, nodes)
            add_relation(
                {"source": bulletin_node["id"], "target": actor["id"], "type": r.related_as or ""},
                relations,
            )

        # Incidents
        itob_relations = Itob.query.filter(Itob.bulletin_id == bulletin_id).all()
        for r in itob_relations:
            incident = create_node(r.incident.id, r.incident.title, Incident)
            add_node(incident, nodes)
            add_relation(
                {
                    "source": bulletin_node["id"],
                    "target": incident["id"],
                    "type": r.related_as or "",
                },
                relations,
            )

        # Locations
        location_relations = (
            db.session.query(bulletin_locations)
            .filter(bulletin_locations.c.bulletin_id == bulletin_id)
            .all()
        )

        for r in location_relations:
            location_id = r.location_id
            location = Location.query.get(location_id)

            # Create a location node
            location_node = create_node(location.id, location.title, Location)
            add_node(location_node, nodes)

            # Add relation between bulletin and location
            add_relation(
                {"source": bulletin_node["id"], "target": location_node["id"], "type": "location"},
                relations,
            )

        # Event locations related to the bulletin
        event_relations = (
            db.session.query(Event)
            .join(bulletin_events, (bulletin_events.c.event_id == Event.id))
            .filter(bulletin_events.c.bulletin_id == bulletin_id)
            .all()
        )

        for event in event_relations:
            if event.location:
                event_location_node = create_node(event.location.id, event.location.title, Location)
                add_node(event_location_node, nodes)

                # Add relation between bulletin and location
                add_relation(
                    {
                        "source": bulletin_node["id"],
                        "target": event_location_node["id"],
                        "type": "location",
                    },
                    relations,
                )

        return json.dumps({"nodes": nodes, "links": relations})

    @staticmethod
    def get_actor_graph(actor_id):
        nodes = []
        relations = []

        # Actor to Actor (Atoa)
        atoa_relations = Atoa.query.filter(
            or_(Atoa.actor_id == actor_id, Atoa.related_actor_id == actor_id)
        ).all()

        for r in atoa_relations:
            source_actor = create_node(r.actor_from.id, r.actor_from.name, Actor)
            target_actor = create_node(r.actor_to.id, r.actor_to.name, Actor)

            add_node(source_actor, nodes)
            add_node(target_actor, nodes)

            add_relation(
                {
                    "source": source_actor["id"],
                    "target": target_actor["id"],
                    "type": r.related_as or "",
                },
                relations,
            )

        # add actor node
        actor_node = create_node(actor_id, Actor.query.get(actor_id).name, Actor)
        add_node(actor_node, nodes)

        # Actors to Bulletins
        atob_relations = Atob.query.filter(Atob.actor_id == actor_id).all()
        for r in atob_relations:
            actor = create_node(actor_id, Actor.query.get(actor_id).name, Actor)
            bulletin = create_node(r.bulletin.id, r.bulletin.title, Bulletin)

            add_node(actor, nodes)
            add_node(bulletin, nodes)

            add_relation(
                {"source": actor_node["id"], "target": bulletin["id"], "type": r.related_as or ""},
                relations,
            )

        # Incident to Actor (Itoa)
        itoa_relations = Itoa.query.filter(Itoa.actor_id == actor_id).all()
        for r in itoa_relations:
            incident = create_node(r.incident.id, r.incident.title, Incident)
            add_node(incident, nodes)
            add_relation(
                {"source": incident["id"], "target": actor_node["id"], "type": r.related_as or ""},
                relations,
            )

        # Event locations related to the actor
        event_relations = (
            db.session.query(Event)
            .join(actor_events, (actor_events.c.event_id == Event.id))
            .filter(actor_events.c.actor_id == actor_id)
            .all()
        )

        for event in event_relations:
            if event.location:
                event_location_node = create_node(event.location.id, event.location.title, Location)
                add_node(event_location_node, nodes)

                # Add relation between actor and location
                add_relation(
                    {
                        "source": actor_node["id"],
                        "target": event_location_node["id"],
                        "type": "location",
                    },
                    relations,
                )

        return json.dumps({"nodes": nodes, "links": relations})

    @staticmethod
    def get_incident_graph(incident_id):
        nodes = []
        relations = []

        # Incident to Incident (Itoi)
        itoi_relations = Itoi.query.filter(
            or_(Itoi.incident_id == incident_id, Itoi.related_incident_id == incident_id)
        ).all()

        for r in itoi_relations:
            source_incident = create_node(r.incident_from.id, r.incident_from.title, Incident)
            target_incident = create_node(r.incident_to.id, r.incident_to.title, Incident)

            add_node(source_incident, nodes)
            add_node(target_incident, nodes)

            add_relation(
                {
                    "source": source_incident["id"],
                    "target": target_incident["id"],
                    "type": r.related_as or "",
                },
                relations,
            )

        # add incident node
        incident_node = create_node(incident_id, Incident.query.get(incident_id).title, Incident)
        add_node(incident_node, nodes)

        # Incidents to Bulletins
        itob_relations = Itob.query.filter(Itob.incident_id == incident_id).all()
        for r in itob_relations:
            incident = create_node(r.incident.id, r.incident.title, Incident)
            bulletin = create_node(r.bulletin.id, r.bulletin.title, Bulletin)

            add_node(incident, nodes)
            add_node(bulletin, nodes)

            add_relation(
                {
                    "source": incident_node["id"],
                    "target": bulletin["id"],
                    "type": r.related_as or "",
                },
                relations,
            )

        # Incident to Actor (Itoa)
        itoa_relations = Itoa.query.filter(Itoa.incident_id == incident_id).all()
        for r in itoa_relations:
            actor = create_node(r.actor.id, r.actor.title, Actor)
            add_node(actor, nodes)
            add_relation(
                {"source": incident_node["id"], "target": actor["id"], "type": r.related_as or ""},
                relations,
            )

        # Incident locations
        # Assuming the secondary table is named incident_locations
        location_relations = (
            db.session.query(incident_locations)
            .filter(incident_locations.c.incident_id == incident_id)
            .all()
        )

        for r in location_relations:
            location_id = r.location_id
            location = Location.query.get(location_id)

            if location:
                location_node = create_node(location.id, location.title, Location)
                add_node(location_node, nodes)

                # Add relation between incident and location
                add_relation(
                    {
                        "source": incident_node["id"],
                        "target": location_node["id"],
                        "type": "location",
                    },
                    relations,
                )

        # Event locations related to the incident
        event_relations = (
            db.session.query(Event)
            .join(incident_events, (incident_events.c.event_id == Event.id))
            .filter(incident_events.c.incident_id == incident_id)
            .all()
        )

        for event in event_relations:
            if event.location:
                event_location_node = create_node(event.location.id, event.location.title, Location)
                add_node(event_location_node, nodes)

                # Add relation between incident and location
                add_relation(
                    {
                        "source": incident_node["id"],
                        "target": event_location_node["id"],
                        "type": "location",
                    },
                    relations,
                )

        return json.dumps({"nodes": nodes, "links": relations})

    @staticmethod
    def merge_graphs(graph_json1, graph_json2):
        # Parse JSON strings to dictionaries
        graph1 = json.loads(graph_json1)
        graph2 = json.loads(graph_json2)

        merged_nodes = graph1["nodes"]
        merged_links = graph1["links"]

        # Function to check if a node exists
        def node_exists(node, nodes):
            return any(n["id"] == node["id"] for n in nodes)

        # Function to check if a link exists
        def link_exists(link, links):
            return any(
                l["source"] == link["source"] and l["target"] == link["target"] for l in links
            )

        # Merge nodes
        for node in graph2["nodes"]:
            if not node_exists(node, merged_nodes):
                merged_nodes.append(node)

        # Merge links
        for link in graph2["links"]:
            if not link_exists(link, merged_links):
                merged_links.append(link)

        return json.dumps({"nodes": merged_nodes, "links": merged_links})

    @staticmethod
    def expanded_graph(entity_type, entity_id):
        # Fetch the entity class based on the entity_type
        entity_class = class_mapping.get(entity_type)
        if not entity_class:
            raise ValueError("Invalid entity type")

        # Get the item from the database
        item = entity_class.query.get(entity_id)
        if not item:
            raise ValueError("Entity not found")

        # Call the related method to get entities_dict
        entities_dict = item.related(include_self=True)
        combined_graph = None
        # Iterate over each entity type and their IDs
        for entity_type, entity_ids in entities_dict.items():
            for entity_id in entity_ids:
                # Generate the graph for the current entity
                current_graph = GraphUtils.get_graph_json(entity_type, entity_id)

                # If this is the first entity, initialize combined_graph
                if combined_graph is None:
                    combined_graph = current_graph
                else:
                    # Merge the current graph with the combined graph
                    combined_graph = GraphUtils.merge_graphs(combined_graph, current_graph)

        return combined_graph
