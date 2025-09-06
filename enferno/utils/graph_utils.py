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
    Location,
    Event,
    AtobInfo,
    BtobInfo,
    ItoaInfo,
    ItobInfo,
    ItoiInfo,
    AtoaInfo,
)
from enferno.extensions import db
from enferno.admin.models.tables import (
    bulletin_locations,
    incident_locations,
    actor_events,
    bulletin_events,
    incident_events,
)

class_mapping = {
    "bulletin": Bulletin,
    "actor": Actor,
    "incident": Incident,
    "location": Location,
}


class GraphUtils:
    def __init__(self, user=None):
        self.user = user

    def add_node(self, node, node_list):
        if node not in node_list:
            node_list.append(node)

    def add_relation(self, relation, relations_list):
        if relation not in relations_list:
            relations_list.append(relation)

    def create_node(self, id, model):
        # Restrict by default
        word_mask = "RESTRICTED"
        title = word_mask
        instance = model.query.get(id)

        if instance and model.__tablename__ in ["actor", "incident", "bulletin"]:
            if self.user and self.user.can_access(instance):
                title = instance.title
        elif instance and model.__tablename__ == "location":
            title = instance.title

        return {
            "id": f"{model.__name__}{id}",
            "_id": id,
            "title": title,
            "color": model.COLOR,
            "type": model.__name__,
            "collapsed": True,
            "childLinks": [],
            "restricted": title == word_mask,
        }

    def get_legend(self):
        return {entity: class_mapping[entity].COLOR for entity in class_mapping}

    @staticmethod
    def get_relation_titles(relation_type, relation_ids):
        info_classes = {
            "Atob": AtobInfo,
            "Btob": BtobInfo,
            "Itoa": ItoaInfo,
            "Itob": ItobInfo,
            "Itoi": ItoiInfo,
            "Atoa": AtoaInfo,
        }
        info_class = info_classes.get(relation_type)
        if info_class and relation_ids:
            if isinstance(relation_ids, list):
                return ", ".join(
                    info_class.query.get(rid).title if info_class.query.get(rid) else str(rid)
                    for rid in relation_ids
                )
            else:
                info = info_class.query.get(relation_ids)
                return info.title if info else str(relation_ids)
        return str(relation_ids) if relation_ids else ""

    def get_graph_json(self, entity_type: str, entity_id: int) -> str:
        if entity_type not in class_mapping:
            raise ValueError("Invalid entity type")

        graph_json = {}
        if entity_type == "bulletin":
            graph_json = self.get_bulletin_graph(entity_id)
        elif entity_type == "actor":
            graph_json = self.get_actor_graph(entity_id)
        elif entity_type == "incident":
            graph_json = self.get_incident_graph(entity_id)
        else:
            raise ValueError("Unsupported entity type")

        graph_json["legend"] = self.get_legend()
        return json.dumps(graph_json)

    def get_bulletin_graph(self, bulletin_id: int) -> dict:
        nodes = []
        relations = []

        bulletin_node = self.create_node(bulletin_id, Bulletin)
        self.add_node(bulletin_node, nodes)

        btob_relations = Btob.query.filter(
            or_(Btob.bulletin_id == bulletin_id, Btob.related_bulletin_id == bulletin_id)
        ).all()

        for r in btob_relations:
            source_bulletin = self.create_node(r.bulletin_from.id, Bulletin)
            target_bulletin = self.create_node(r.bulletin_to.id, Bulletin)

            self.add_node(source_bulletin, nodes)
            self.add_node(target_bulletin, nodes)

            relation_titles = self.get_relation_titles("Btob", r.related_as)
            self.add_relation(
                {
                    "source": source_bulletin["id"],
                    "target": target_bulletin["id"],
                    "type": relation_titles,
                },
                relations,
            )

        self._add_related_entities_to_bulletin(bulletin_id, nodes, relations)

        return {"nodes": nodes, "links": relations}

    def _add_related_entities_to_bulletin(self, bulletin_id: int, nodes: list, relations: list):
        atob_relations = Atob.query.filter(Atob.bulletin_id == bulletin_id).all()
        for r in atob_relations:
            actor_node = self.create_node(r.actor.id, Actor)
            self.add_node(actor_node, nodes)
            relation_titles = self.get_relation_titles("Atob", r.related_as)
            self.add_relation(
                {"source": nodes[0]["id"], "target": actor_node["id"], "type": relation_titles},
                relations,
            )

        itob_relations = Itob.query.filter(Itob.bulletin_id == bulletin_id).all()
        for r in itob_relations:
            incident_node = self.create_node(r.incident.id, Incident)
            self.add_node(incident_node, nodes)
            relation_titles = self.get_relation_titles("Itob", r.related_as)
            self.add_relation(
                {"source": nodes[0]["id"], "target": incident_node["id"], "type": relation_titles},
                relations,
            )

        location_relations = (
            db.session.query(bulletin_locations)
            .filter(bulletin_locations.c.bulletin_id == bulletin_id)
            .all()
        )
        for r in location_relations:
            location_node = self.create_node(r.location_id, Location)
            self.add_node(location_node, nodes)
            self.add_relation(
                {"source": nodes[0]["id"], "target": location_node["id"], "type": "location"},
                relations,
            )

        event_relations = (
            db.session.query(Event)
            .join(bulletin_events, (bulletin_events.c.event_id == Event.id))
            .filter(bulletin_events.c.bulletin_id == bulletin_id)
            .all()
        )
        for event in event_relations:
            if event.location:
                event_location_node = self.create_node(event.location.id, Location)
                self.add_node(event_location_node, nodes)
                self.add_relation(
                    {
                        "source": nodes[0]["id"],
                        "target": event_location_node["id"],
                        "type": "location",
                    },
                    relations,
                )

    def get_actor_graph(self, actor_id: int) -> dict:
        nodes = []
        relations = []

        actor_node = self.create_node(actor_id, Actor)
        self.add_node(actor_node, nodes)

        atoa_relations = Atoa.query.filter(
            or_(Atoa.actor_id == actor_id, Atoa.related_actor_id == actor_id)
        ).all()

        for r in atoa_relations:
            source_actor = self.create_node(r.actor_from.id, Actor)
            target_actor = self.create_node(r.actor_to.id, Actor)

            self.add_node(source_actor, nodes)
            self.add_node(target_actor, nodes)

            relation_titles = self.get_relation_titles("Atoa", r.related_as)
            self.add_relation(
                {
                    "source": source_actor["id"],
                    "target": target_actor["id"],
                    "type": relation_titles,
                },
                relations,
            )

        self._add_related_entities_to_actor(actor_id, nodes, relations)

        return {"nodes": nodes, "links": relations}

    def _add_related_entities_to_actor(self, actor_id: int, nodes: list, relations: list):
        atob_relations = Atob.query.filter(Atob.actor_id == actor_id).all()
        for r in atob_relations:
            bulletin_node = self.create_node(r.bulletin.id, Bulletin)
            self.add_node(bulletin_node, nodes)
            relation_titles = self.get_relation_titles("Atob", r.related_as)
            self.add_relation(
                {"source": nodes[0]["id"], "target": bulletin_node["id"], "type": relation_titles},
                relations,
            )

        itoa_relations = Itoa.query.filter(Itoa.actor_id == actor_id).all()
        for r in itoa_relations:
            incident_node = self.create_node(r.incident.id, Incident)
            self.add_node(incident_node, nodes)
            relation_titles = self.get_relation_titles("Itoa", r.related_as)
            self.add_relation(
                {"source": incident_node["id"], "target": nodes[0]["id"], "type": relation_titles},
                relations,
            )

        event_relations = (
            db.session.query(Event)
            .join(actor_events, (actor_events.c.event_id == Event.id))
            .filter(actor_events.c.actor_id == actor_id)
            .all()
        )
        for event in event_relations:
            if event.location:
                event_location_node = self.create_node(event.location.id, Location)
                self.add_node(event_location_node, nodes)
                self.add_relation(
                    {
                        "source": nodes[0]["id"],
                        "target": event_location_node["id"],
                        "type": "location",
                    },
                    relations,
                )

    def get_incident_graph(self, incident_id: int) -> dict:
        nodes = []
        relations = []

        incident_node = self.create_node(incident_id, Incident)
        self.add_node(incident_node, nodes)

        itoi_relations = Itoi.query.filter(
            or_(Itoi.incident_id == incident_id, Itoi.related_incident_id == incident_id)
        ).all()

        for r in itoi_relations:
            source_incident = self.create_node(r.incident_from.id, Incident)
            target_incident = self.create_node(r.incident_to.id, Incident)

            self.add_node(source_incident, nodes)
            self.add_node(target_incident, nodes)

            relation_titles = self.get_relation_titles("Itoi", r.related_as)
            self.add_relation(
                {
                    "source": source_incident["id"],
                    "target": target_incident["id"],
                    "type": relation_titles,
                },
                relations,
            )

        self._add_related_entities_to_incident(incident_id, nodes, relations)

        return {"nodes": nodes, "links": relations}

    def _add_related_entities_to_incident(self, incident_id: int, nodes: list, relations: list):
        itob_relations = Itob.query.filter(Itob.incident_id == incident_id).all()
        for r in itob_relations:
            bulletin_node = self.create_node(r.bulletin.id, Bulletin)
            self.add_node(bulletin_node, nodes)
            relation_titles = self.get_relation_titles("Itob", r.related_as)
            self.add_relation(
                {"source": nodes[0]["id"], "target": bulletin_node["id"], "type": relation_titles},
                relations,
            )

        itoa_relations = Itoa.query.filter(Itoa.incident_id == incident_id).all()
        for r in itoa_relations:
            actor_node = self.create_node(r.actor.id, Actor)
            self.add_node(actor_node, nodes)
            relation_titles = self.get_relation_titles("Itoa", r.related_as)
            self.add_relation(
                {"source": nodes[0]["id"], "target": actor_node["id"], "type": relation_titles},
                relations,
            )

        location_relations = (
            db.session.query(incident_locations)
            .filter(incident_locations.c.incident_id == incident_id)
            .all()
        )
        for r in location_relations:
            location_node = self.create_node(r.location_id, Location)
            self.add_node(location_node, nodes)
            self.add_relation(
                {"source": nodes[0]["id"], "target": location_node["id"], "type": "location"},
                relations,
            )

        event_relations = (
            db.session.query(Event)
            .join(incident_events, (incident_events.c.event_id == Event.id))
            .filter(incident_events.c.incident_id == incident_id)
            .all()
        )
        for event in event_relations:
            if event.location:
                event_location_node = self.create_node(event.location.id, Location)
                self.add_node(event_location_node, nodes)
                self.add_relation(
                    {
                        "source": nodes[0]["id"],
                        "target": event_location_node["id"],
                        "type": "location",
                    },
                    relations,
                )

    @staticmethod
    def merge_graphs(graph_json1: str, graph_json2: str) -> str:
        graph1 = json.loads(graph_json1)
        graph2 = json.loads(graph_json2)

        def node_exists(node, nodes):
            return any(n["id"] == node["id"] for n in nodes)

        def link_exists(link, links):
            return any(
                l["source"] == link["source"] and l["target"] == link["target"] for l in links
            )

        merged_nodes = graph1["nodes"]
        merged_links = graph1["links"]

        for node in graph2["nodes"]:
            if not node_exists(node, merged_nodes):
                merged_nodes.append(node)

        for link in graph2["links"]:
            if not link_exists(link, merged_links):
                merged_links.append(link)

        merged_graph = {"nodes": merged_nodes, "links": merged_links}
        merged_graph["legend"] = GraphUtils().get_legend()

        return json.dumps(merged_graph)

    def expanded_graph(self, entity_type: str, entity_id: int) -> str:
        entity_class = class_mapping.get(entity_type)
        if not entity_class:
            raise ValueError("Invalid entity type")

        item = entity_class.query.get(entity_id)
        if not item:
            raise ValueError("Entity not found")

        entities_dict = item.related(include_self=True)
        combined_graph = None

        for entity_type, entity_ids in entities_dict.items():
            for entity_id in entity_ids:
                current_graph = self.get_graph_json(entity_type, entity_id)

                if combined_graph is None:
                    combined_graph = current_graph
                else:
                    combined_graph = self.merge_graphs(combined_graph, current_graph)

        return combined_graph
