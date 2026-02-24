# -*- coding: utf-8 -*-
from datetime import datetime, timezone

from enferno.admin.models.Notification import Notification
from enferno.extensions import db
from enferno.tasks import celery
from enferno.utils.email_utils import EmailUtils
from enferno.utils.logging_utils import get_logger

logger = get_logger("celery.tasks.notifications")


@celery.task(bind=True, max_retries=3)
def send_email_notification(self, notification_id: int) -> bool:
    """
    Send email notification with retry logic - simplified status tracking.

    Args:
        notification_id: ID of the notification to send

    Returns:
        bool: True if email was sent successfully, False otherwise
    """

    # Get the notification record
    notification = db.session.get(Notification, notification_id)
    if not notification:
        logger.error(f"Notification {notification_id} not found")
        return False

    if notification.email_sent:
        logger.info(f"Notification {notification_id} already sent; skipping send")
        return True

    # Check if user has email (should be validated already, but double-check)
    if not notification.user.email:
        logger.error(f"User {notification.user.id} has no email address")
        return False

    success = EmailUtils.send_email(
        recipient=notification.user.email,
        subject=notification.title,
        body=f"{notification.message}",
    )

    if success:
        notification.email_sent = True
        notification.email_sent_at = datetime.now(timezone.utc)
        notification.save()
        logger.info(
            f"Email notification {notification_id} sent successfully to {notification.user.id}"
        )
        return True

    else:
        # Retry if retries remaining
        if self.request.retries < self.max_retries:
            logger.info(
                f"Retrying email notification {notification_id}... (attempt {self.request.retries + 1})"
            )
            raise self.retry(countdown=60 * (2**self.request.retries))

        # Log failure after retries exhausted
        logger.error(
            f"Failed to send email notification {notification_id} after {self.max_retries} retries"
        )
        return False
