from __future__ import annotations

from flask import Response, json
from flask_security.decorators import current_user

from enferno.utils.background_search import get_result
from enferno.utils.http_response import HTTPResponse

from . import admin


@admin.route("/api/background-search/<token>")
def api_background_search(token: str) -> Response:
    """Return the stored ids of a completed background search (owner only)."""
    result = get_result(token)
    if not result or result["user_id"] != current_user.id:
        return HTTPResponse.not_found()
    return Response(
        json.dumps({"entity": result["entity"], "ids": result["ids"]}),
        content_type="application/json",
    )
