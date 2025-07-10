import re
import unicodedata
from html import unescape
from wtforms.validators import ValidationError
from email_validator import validate_email, EmailNotValidError


def validate_plain_text_field(
    field_data: str,
    field_name: str = "Field",
    max_length: int = 64,
    check_unicode: bool = False,
    allowed_unciode_categories: set[chr] = {"L", "N"},
    other_allowed_chars: set[chr] = {"_", "-"},
) -> None:
    """
    Validates that a field contains only plain text and rejects any HTML content.

    This function explicitly rejects HTML tags, HTML entities, and overly long strings
    instead of silently sanitizing them, providing clear feedback to users.

    If check_unicode is True, the function will also validate that the field contains only Unicode characters
    in the allowed_unciode_categories or other_allowed_chars set.

    Args:
        field_data: The field data to validate
        field_name: The name of the field for error messages (default: "Field")
        max_length: Maximum allowed length for the field (default: 64)
        check_unicode: Whether to check for Unicode characters (default: False)
        allowed_unciode_categories: Set of Unicode categories to allow (default: {'L', 'N'})
        other_allowed_chars: Set of other characters to allow (default: {'_', '-'})

    Raises:
        ValidationError: If the field contains HTML, entities, is too long, or contains invalid Unicode characters
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

    if check_unicode and (allowed_unciode_categories or other_allowed_chars):
        for char in clean_name:
            if other_allowed_chars and char in other_allowed_chars:
                continue
            if unicodedata.category(char)[0] not in allowed_unciode_categories:
                raise ValidationError(f"{field_name} contains invalid characters.")


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
