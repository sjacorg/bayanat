from __future__ import annotations

from flask import Response, request, current_app, jsonify
from flask_security.decorators import current_user, roles_accepted
import shortuuid

from enferno.admin.models import Bulletin, Activity
from enferno.admin.models.Notification import Notification
from enferno.admin.validation.models import WebImportValidationModel
from enferno.data_import.models import DataImport
from enferno.extensions import db
from enferno.tasks import download_media_from_web
from enferno.utils.http_response import HTTPResponse
from enferno.utils.logging_utils import get_logger
from enferno.utils.validation_utils import validate_with
from . import admin

logger = get_logger()


# Notifications
@admin.route("/api/notifications")
def api_notifications():
    """
    Returns paginated notifications with stats in a single optimized query.
    Query params: page, per_page (max 50), status (read/unread), is_urgent (true/false)
    """
    # Parse parameters with defaults and validation
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 50)
    status = request.args.get("status")
    is_urgent = request.args.get("is_urgent")

    # Single efficient query with combined pagination and stats
    paginated, unread_count, has_urgent_unread = Notification.get_paginated_with_stats(
        user_id=current_user.id, page=page, per_page=per_page, status=status, is_urgent=is_urgent
    )

    # Optimize unread count when filtering by unread status
    if status == "unread":
        unread_count = paginated.total

    return jsonify(
        {
            "items": [n.to_dict() for n in paginated.items],
            "currentPage": page,
            "perPage": per_page,
            "total": paginated.total,
            "hasMore": paginated.has_next,
            "unreadCount": unread_count,
            "hasUnreadUrgentNotifications": has_urgent_unread,
        }
    )


@admin.route("/api/notifications/<int:notification_id>/read", methods=["POST"])
def api_mark_notification_read(notification_id):
    """Mark a specific notification as read."""
    notification = db.session.get(Notification, notification_id)

    if not notification or notification.user_id != current_user.id:
        return HTTPResponse.NOT_FOUND

    try:
        notification.mark_as_read()
        return jsonify(
            {"message": "Notification marked as read", "notification": notification.to_dict()}
        )
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}", exc_info=True)
        return HTTPResponse.INTERNAL_SERVER_ERROR


@admin.route("/api/notifications/mark-all-read", methods=["POST"])
def api_mark_all_notifications_read():
    """Mark all notifications as read for current user."""
    try:
        Notification.mark_all_read_for_user(current_user.id)
        unread_count = Notification.get_unread_count(current_user.id)
        return jsonify({"message": "All notifications marked as read", "unreadCount": unread_count})
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}", exc_info=True)
        return HTTPResponse.INTERNAL_SERVER_ERROR


@admin.post("/api/bulletin/web")
@roles_accepted("Admin", "DA")
@validate_with(WebImportValidationModel)
def api_bulletin_web_import(validated_data: dict) -> Response:
    """Import bulletin from web URL"""

    if not current_app.config.get("WEB_IMPORT"):
        return HTTPResponse.forbidden("Web import is disabled")

    if not (current_user.has_role("Admin") or current_user.can_import_web):
        return HTTPResponse.forbidden("Restricted Access")

    url = validated_data["url"]

    # Check for duplicate URL
    existing_bulletin = Bulletin.query.filter(Bulletin.source_link == url).first()
    if existing_bulletin:
        return HTTPResponse.error(
            f"Duplicate URL: This URL has already been imported in bulletin #{existing_bulletin.id}",
            status=409,
        )

    # Create import log
    data_import = DataImport(
        user_id=current_user.id,
        table="bulletin",
        file=url,
        batch_id=shortuuid.uuid()[:9],
        data={
            "mode": 3,  # Web import mode
            "optimize": False,
            "sources": [],
            "labels": [],
            "ver_labels": [],
            "locations": [],
            "tags": [],
            "roles": [],
        },
    )
    data_import.add_to_log(f"Started download from {url}")
    data_import.save()

    # Start async download
    download_media_from_web.delay(
        url=url, user_id=current_user.id, batch_id=data_import.batch_id, import_id=data_import.id
    )

    return HTTPResponse.success(data={"batch_id": data_import.batch_id}, status=202)
