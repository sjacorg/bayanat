# -*- coding: utf-8 -*-
"""Timeout-then-queue search.

Interactive searches run under a bounded Postgres statement_timeout. When the
database cancels one, the same query is re-run by a Celery worker without the
interactive bound, the matching ids are stored in Redis for a day, and the user
gets a notification whose link replays the stored ids in the normal list view.
"""

import json
import secrets
from functools import wraps

from flask import Response, current_app
from flask_security import current_user
from psycopg2.errors import QueryCanceled
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from enferno.extensions import db, rds

RESULT_TTL = 24 * 60 * 60
MAX_RESULTS = 10_000
_KEY = "background_search:{}"


def apply_search_timeout() -> None:
    """Bound every statement in the current transaction (no-op when SEARCH_TIMEOUT is 0).

    Uses SET LOCAL, so the bound dies with the transaction and never leaks
    through the connection pool. Call after any commit (e.g. activity logging),
    otherwise the commit ends the transaction and drops the bound.
    """
    seconds = current_app.config.get("SEARCH_TIMEOUT", 0)
    if seconds:
        db.session.execute(text(f"SET LOCAL statement_timeout = {int(seconds * 1000)}"))


def search_timed_out(error: Exception) -> bool:
    return isinstance(error, OperationalError) and isinstance(error.orig, QueryCanceled)


def queue_search(user_id: int, entity: str, q: list) -> str:
    from enferno.tasks import background_search

    token = secrets.token_urlsafe(16)
    background_search.delay(token, user_id, entity, q)
    return token


def store_result(token: str, user_id: int, entity: str, ids: list) -> None:
    rds.set(
        _KEY.format(token),
        json.dumps({"user_id": user_id, "entity": entity, "ids": ids}),
        ex=RESULT_TTL,
    )


def get_result(token: str) -> dict | None:
    payload = rds.get(_KEY.format(token))
    return json.loads(payload) if payload else None


def timeout_fallback(entity: str):
    """Turn a search endpoint's statement timeout into a queued background search (202)."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except OperationalError as error:
                if not search_timed_out(error):
                    raise
                db.session.rollback()
                q = kwargs.get("validated_data", {}).get("q", [{}])
                token = queue_search(current_user.id, entity, q)
                return Response(
                    json.dumps(
                        {
                            "queued": True,
                            "token": token,
                            "message": "This search is taking long, so it continues in the "
                            "background. You will be notified when results are ready.",
                        }
                    ),
                    status=202,
                    content_type="application/json",
                )

        return wrapper

    return decorator
