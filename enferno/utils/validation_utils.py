import re
from html import unescape
from wtforms.validators import ValidationError
from zxcvbn import zxcvbn


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


def validate_password_zxcvbn(password: str, minimum_score: int = 3) -> tuple[bool, int]:
    """
    Validates a password using zxcvbn.
    """
    result = zxcvbn(password)
    score = result.get("score")
    return score >= minimum_score, score
