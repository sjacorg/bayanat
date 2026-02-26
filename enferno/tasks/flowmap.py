# -*- coding: utf-8 -*-
import hashlib
import json
from typing import Optional

from enferno.extensions import db, rds
from enferno.tasks import celery
from enferno.utils.flowmap_utils import FlowmapUtils
from enferno.utils.logging_utils import get_logger
from enferno.utils.search_utils import SearchUtils

logger = get_logger("celery.tasks.flowmap")


@celery.task
def generate_actor_flowmap(query_json: list, user_id: int) -> Optional[str]:
    """
    Generate flowmap visualization data from actor life events.
    Returns {locations, flows, metadata} JSON cached in Redis.
    Query format: [{}] for all actors, or [{field: value}] for filtered.
    """
    if not user_id:
        raise ValueError("User ID is required to generate actor flowmap")

    logger.info(f"Starting flowmap generation for user {user_id}")

    try:
        # Create cache key based on query + user
        normalized_query = json.dumps(query_json, sort_keys=True)
        combined_string = f"{normalized_query}-actor-{user_id}"
        query_key = hashlib.sha256(combined_string.encode()).hexdigest()

        # Redis keys for this user's flowmap
        status_key = f"user{user_id}:flowmap:status"
        data_key = f"user{user_id}:flowmap:data"
        query_key_key = f"user{user_id}:flowmap:query_key"
        error_key = f"user{user_id}:flowmap:error"

        # Check if we already have data for this exact query
        existing_query_key = rds.get(query_key_key)
        if existing_query_key and existing_query_key.decode() == query_key:
            logger.info(f"Returning cached flowmap data for user {user_id}")
            existing_data = rds.get(data_key)
            if existing_data:
                return existing_data.decode()

        # Set status to pending
        rds.set(status_key, "pending")
        rds.delete(error_key)

        # Fetch matching actors using SearchUtils (enforces access controls)
        search_util = SearchUtils(query_json, cls="actor")
        query = search_util.get_query()
        result = db.session.execute(query)
        actors = result.scalars().unique().all()

        logger.info(f"Found {len(actors)} actors for flowmap generation")

        # Generate flowmap data using utility
        flowmap_data = FlowmapUtils.generate_from_actors(actors)
        flowmap_json = json.dumps(flowmap_data)

        # Cache the result
        rds.set(data_key, flowmap_json)
        rds.set(query_key_key, query_key)
        rds.set(status_key, "done")

        return flowmap_json

    except Exception as e:
        error_msg = f"Error generating flowmap: {str(e)}"
        logger.error(error_msg, exc_info=True)
        rds.set(f"user{user_id}:flowmap:status", "error")
        rds.set(f"user{user_id}:flowmap:error", error_msg)
        raise
