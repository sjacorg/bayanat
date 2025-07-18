from flask_mail import Message
from enferno.extensions import mail
from enferno.utils.logging_utils import get_logger
import logging

logger = get_logger()

# Configure Flask-Mail's logger to use our custom logger
mail_logger = logging.getLogger("flask_mail")
mail_logger.parent = logger
mail_logger.propagate = True


class EmailUtils:
    """
    Utility class for sending emails.
    """

    @staticmethod
    def send_email(recipient: str, subject: str, body: str) -> bool:
        """
        Send an email using Flask-Mail.

        Args:
            recipient: Email address of the recipient
            subject: Subject of the email
            body: Body text of the email

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            if not recipient:
                logger.error("No recipient email address provided")
                return False

            msg = Message(
                subject=subject,
                recipients=[recipient],
                body=body,
            )

            mail.send(msg)
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}", exc_info=True)
            return False
