# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from smtplib import SMTPAuthenticationError

from enferno.admin.models.Notification import Notification
from enferno.extensions import db
from enferno.tasks import celery
from enferno.utils.email_utils import EmailUtils
from enferno.utils.logging_utils import get_logger

logger = get_logger("celery.tasks.notifications")


@celery.task(bind=True, max_retries=3)
def send_email_notification(self, notification_id: int) -> bool:
    """
    Send email notification with retry logic.

    Args:
        notification_id: ID of the notification to send

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    notification = db.session.get(Notification, notification_id)
    if not notification:
        logger.error(f"Notification {notification_id} not found")
        return False

    if notification.email_sent:
        return True

    if not notification.user.email:
        logger.error(f"User {notification.user.id} has no email address")
        return False

    try:
        success = EmailUtils.send_email(
            recipient=notification.user.email,
            subject=notification.title,
            body=notification.message,
        )
    except SMTPAuthenticationError:
        logger.error(
            f"Email notification {notification_id} failed: bad SMTP credentials, not retrying"
        )
        return False

    if success:
        notification.email_sent = True
        notification.email_sent_at = datetime.now(timezone.utc)
        notification.save()
        logger.info(f"Email notification {notification_id} sent to user {notification.user.id}")
        return True

    if self.request.retries < self.max_retries:
        logger.info(
            f"Retrying email notification {notification_id} (attempt {self.request.retries + 1})"
        )
        raise self.retry(countdown=60 * (2**self.request.retries))

    logger.error(f"Email notification {notification_id} failed after {self.max_retries} retries")
    return False
