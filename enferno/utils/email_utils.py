from smtplib import SMTPAuthenticationError

from flask_mail import Message

from enferno.extensions import mail
from enferno.utils.logging_utils import get_logger

logger = get_logger()


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

        Raises:
            SMTPAuthenticationError: re-raised so callers can skip retries.
        """
        if not recipient:
            logger.error("No recipient email address provided")
            return False

        try:
            msg = Message(
                subject=subject,
                recipients=[recipient],
                body=body,
            )
            mail.send(msg)
            return True

        except SMTPAuthenticationError:
            logger.error("SMTP authentication failed, check mail credentials")
            raise

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
