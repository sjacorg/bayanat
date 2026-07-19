# -*- coding: utf-8 -*-
"""Background continuation of interactive searches that hit SEARCH_TIMEOUT."""

from flask import current_app
from sqlalchemy import text

from enferno.admin.constants import Constants
from enferno.admin.models import Actor, Bulletin, Incident
from enferno.admin.models.Notification import Notification
from enferno.extensions import db
from enferno.tasks import celery
from enferno.user.models import User
from enferno.utils import background_search as results
from enferno.utils.logging_utils import get_logger
from enferno.utils.search_utils import SearchUtils

logger = get_logger()

ENTITY_MODELS = {"bulletin": Bulletin, "actor": Actor, "incident": Incident}


@celery.task
def background_search(token: str, user_id: int, entity: str, q: list) -> None:
    model = ENTITY_MODELS[entity]
    user = db.session.get(User, user_id)
    try:
        limit = current_app.config.get("BACKGROUND_SEARCH_TIME_LIMIT", 600)
        db.session.execute(text(f"SET LOCAL statement_timeout = {int(limit * 1000)}"))
        query = (
            SearchUtils(q, entity)
            .get_query()
            .with_only_columns(model.id, maintain_column_froms=True)
            .order_by(model.id.desc())
            .limit(results.MAX_RESULTS)
        )
        ids = list(dict.fromkeys(db.session.execute(query).scalars()))
    except Exception:
        db.session.rollback()
        logger.exception(f"Background {entity} search failed for user {user_id}")
        Notification.send_notification_for_event(
            Constants.NotificationEvent.BACKGROUND_SEARCH_STATUS,
            user,
            "Search Failed",
            f"Your background {entity} search could not be completed. "
            "Try narrowing the search filters.",
        )
        return

    db.session.rollback()  # end the timed read transaction before writing
    results.store_result(token, user_id, entity, ids)
    capped = "+" if len(ids) == results.MAX_RESULTS else ""
    link = f"/admin/{entity}s/?bgs={token}"
    Notification.send_notification_for_event(
        Constants.NotificationEvent.BACKGROUND_SEARCH_STATUS,
        user,
        "Search Completed",
        f"Your {entity} search finished with {len(ids)}{capped} results. "
        f'<a href="{link}">View results</a> (available for 24 hours).',
    )
