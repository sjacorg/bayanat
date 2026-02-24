# -*- coding: utf-8 -*-
import hashlib
import json
from typing import Any, Optional

import enferno.utils.typing as t
from enferno.admin.models import Actor, Bulletin, Incident
from enferno.extensions import db, rds
from enferno.tasks import celery
from enferno.user.models import User
from enferno.utils.graph_utils import GraphUtils
from enferno.utils.logging_utils import get_logger
from enferno.utils.search_utils import SearchUtils

logger = get_logger("celery.tasks.graph")

type_map = {"bulletin": Bulletin, "actor": Actor, "incident": Incident}


@celery.task
def generate_graph(query_json: Any, entity_type: str, user_id: t.id) -> Optional[str]:
    """
    Generate graph for a given query, with caching to avoid regenerating graphs for identical queries.
    Redis Hash Sample Structure for a user with `user_id`:
    Key: "user:123"
    Fields and Values:
        - "query_key": "most_recent_generate_query_key"
        - "graph_data": "most_recent_generated_graph_data"

    Args:
        - query_json: Query JSON.
        - entity_type: Entity type.
        - user_id: User ID.

    Returns:
        - Graph data.
    """
    if not user_id:
        raise ValueError("User ID is required to generate graph")

    entity_type_lower = entity_type.lower()
    if entity_type_lower not in type_map:
        raise ValueError(f"Unsupported entity type: {entity_type}")

    query_key = create_query_key(query_json, entity_type, user_id)

    # Redis hash key for the user
    user_hash_key = f"user:{user_id}"

    # Retrieve the current query key for the user
    existing_query_key = rds.hget(user_hash_key, "query_key")

    if existing_query_key and existing_query_key.decode() == query_key:
        # Return the existing graph data if query keys match
        existing_graph_data = rds.hget(user_hash_key, "graph_data")
        return existing_graph_data.decode()

    # Generate the graph if no cache hit
    graph_data = process_graph_generation(query_json, entity_type_lower, user_id, query_key)

    # Update the hash with the new query key and graph data
    rds.hset(user_hash_key, "query_key", query_key)
    rds.hset(user_hash_key, "graph_data", graph_data)

    return graph_data


def create_query_key(query_json: Any, entity_type: str, user_id: t.id) -> str:
    """
    Create a unique key based on the query JSON, entity type, and user ID.

    Args:
        - query_json: Query JSON.
        - entity_type: Entity type.
        - user_id: User ID.

    Returns:
        - Query key.
    """
    normalized_query = json.dumps(query_json, sort_keys=True)  # Ensures consistent key generation
    combined_string = f"{normalized_query}-{entity_type}-{user_id}"
    return hashlib.sha256(combined_string.encode()).hexdigest()


def process_graph_generation(
    query_json: Any, entity_type: str, user_id: t.id, query_key: str
) -> Optional[str]:
    """
    The core logic for graph generation, querying, and merging graphs.

    Args:
        - query_json: Query JSON.
        - entity_type: Entity type.
        - user_id: User ID.
        - query_key: Query key.

    Returns:
        - Graph data.
    """
    result_set = get_result_set(query_json, entity_type, type_map)
    rds.set(f"user{user_id}:graph:status", "pending")
    user = User.query.get(user_id)
    graph_utils = GraphUtils(user)
    graph = merge_graphs(result_set, entity_type, graph_utils)

    # Cache the generated graph with the unique query key
    rds.set(query_key, graph)
    rds.set(f"user{user_id}:graph:data", graph)
    rds.set(f"user{user_id}:graph:status", "done")
    return graph


def get_result_set(query_json: Any, entity_type: str, type_map: dict) -> Any:
    """
    Retrieve the result set based on the query JSON and entity type.

    Args:
        - query_json: Query JSON.
        - entity_type: Entity type.
        - type_map: Type map.

    Returns:
        - Result set.
    """
    search_util = SearchUtils(query_json, cls=entity_type)
    query = search_util.get_query()
    result = db.session.execute(query)
    return result


def merge_graphs(result_set: Any, entity_type: str, graph_utils: GraphUtils) -> Optional[str]:
    """
    Merge graphs for each item in the result set.

    Args:
        - result_set: Result set.
        - entity_type: Entity type.
        - user_id: User ID.

    Returns:
        - Merged graph data.
    """
    graph = None
    for item in result_set.scalars().unique().all():
        current_graph = graph_utils.get_graph_json(entity_type, item.id)
        graph = current_graph if graph is None else graph_utils.merge_graphs(graph, current_graph)
    return graph
