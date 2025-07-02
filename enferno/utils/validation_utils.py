import re
import unicodedata
from html import unescape
from wtforms.validators import ValidationError
from email_validator import validate_email, EmailNotValidError


def validate_plain_text_field(
    field_data: str, field_name: str = "Field", max_length: int = 64
) -> None:
    """
    Validates that a field contains only plain text and rejects any HTML content.

    This function explicitly rejects HTML tags, HTML entities, and overly long strings
    instead of silently sanitizing them, providing clear feedback to users.

    Args:
        field_data: The field data to validate
        field_name: The name of the field for error messages (default: "Field")
        max_length: Maximum allowed length for the field (default: 64)

    Raises:
        ValidationError: If the field contains HTML, entities, or is too long
    """
    if not field_data or not field_data.strip():
        raise ValidationError(f"{field_name} cannot be empty.")

    # Reject HTML tags
    if re.search(r"<[^>]*>", field_data):
        raise ValidationError(
            f"{field_name} cannot contain HTML tags. Please enter plain text only."
        )

    # Reject HTML entities
    if unescape(field_data) != field_data:
        raise ValidationError(
            f"{field_name} cannot contain HTML entities. Please enter plain text only."
        )

    # Normalize whitespace and validate length
    clean_name = " ".join(field_data.split())
    if len(clean_name) > max_length:
        raise ValidationError(f"{field_name} is too long (maximum {max_length} characters).")


def validate_username_format(username: str) -> str:
    """
    Validates username format - only allows Unicode letters, numbers, underscores, and hyphens.

    Args:
        username: The username to validate

    Returns:
        str: The validated and trimmed username

    Raises:
        ValidationError: If the username format is invalid
    """
    if not username or not username.strip():
        raise ValidationError("Username cannot be empty.")

    validate_plain_text_field(username, "Username", 255)

    username = username.strip()

    # Check each character using Unicode categories
    # Allow: L (Letters), N (Numbers), plus underscore and hyphen
    for char in username:
        if char in ("_", "-"):
            continue  # Allow underscore and hyphen

        char_category = unicodedata.category(char)[0]
        if char_category not in ["L", "N"]:
            raise ValidationError(
                "Invalid username format. Only letters, numbers, underscores (_), and hyphens (-) are allowed."
            )

    return username


def validate_email_format(email: str) -> str:
    """
    Validates email format including unicode/IDN support.

    Args:
        email: The email address to validate

    Returns:
        str: The normalized email address

    Raises:
        ValidationError: If the email format is invalid
    """
    if not email or not email.strip():
        raise ValidationError("Email cannot be empty.")

    try:
        # Use email-validator library for unicode/IDN support
        # Check DNS to False for practical use (avoid rejecting valid format emails due to DNS issues)
        # TODO: Discuss with team if this should be a config option
        validated_email = validate_email(email.strip(), check_deliverability=False)
        return validated_email.normalized
    except EmailNotValidError as e:
        raise ValidationError(f"Invalid email format: {str(e)}")
