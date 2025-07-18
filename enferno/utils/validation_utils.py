import re
import unicodedata
from html import unescape
from email_validator import validate_email, EmailNotValidError
from functools import wraps
from typing import Any, Type, Annotated
from flask import request
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    GetCoreSchemaHandler,
    ValidationError,
    model_validator,
)
import bleach
from bleach.css_sanitizer import CSSSanitizer, ALLOWED_CSS_PROPERTIES
import pydantic_core
from wtforms.validators import ValidationError as WTFormsValidationError


# =============================================================================
# WTForms-based Validation Functions
# =============================================================================


def validate_plain_text_field(
    field_data: str,
    field_name: str = "Field",
    max_length: int = 64,
    allow_unicode: bool = False,
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
        allow_unicode: Whether to allow Unicode characters (default: False)
        allowed_unciode_categories: Set of Unicode categories to allow (default: {'L', 'N'}) (only used if allow_unicode is True)
        other_allowed_chars: Set of other characters to allow (default: {'_', '-'}) (only used if allow_unicode is True)

    Raises:
        ValidationError: If the field contains HTML, entities, is too long, or contains invalid Unicode characters
    """
    if not field_data or not field_data.strip():
        raise WTFormsValidationError(f"{field_name} cannot be empty.")

    # Reject HTML tags
    if re.search(r"<[^>]*>", field_data):
        raise WTFormsValidationError(
            f"{field_name} cannot contain HTML tags. Please enter plain text only."
        )

    # Reject HTML entities
    if unescape(field_data) != field_data:
        raise WTFormsValidationError(
            f"{field_name} cannot contain HTML entities. Please enter plain text only."
        )

    # Normalize whitespace and validate length
    clean_name = " ".join(field_data.split())
    if len(clean_name) > max_length:
        raise ValidationError(f"{field_name} is too long (maximum {max_length} characters).")

    if not allow_unicode:
        if re.search(r"[^a-zA-Z0-9\s]", clean_name):
            raise ValidationError(
                f"{field_name} contains invalid characters. Please enter plain text/numbers only."
            )

    elif allow_unicode and (allowed_unciode_categories or other_allowed_chars):
        for char in clean_name:
            if other_allowed_chars and char in other_allowed_chars:
                continue
            if unicodedata.category(char)[0] not in allowed_unciode_categories:
                raise ValidationError(f"{field_name} contains invalid character: {char}")


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


# =============================================================================
# Pydantic-based Validation Functions and Classes
# =============================================================================


def sanitize_string(value: str) -> str:
    """
    Sanitizes a string by removing any potentially harmful HTML tags.

    Args:
        - value: The string to be sanitized.

    Returns:
        - The sanitized string.

    """
    # We'll allow the following tags
    value = bleach.clean(
        value,
        tags=[
            "p",
            "br",
            "a",
            "strong",
            "em",
            "ul",
            "ol",
            "li",
            "span",
            "div",
            "img",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "blockquote",
            "table",
            "caption",
            "tbody",
            "thead",
            "tfoot",
            "tr",
            "th",
            "td",
            "u",
            "s",
            "strike",
        ],
        attributes={
            "*": ["style"],
            "a": ["href", "title", "target"],
            "img": ["src", "alt", "width", "height"],
            "table": ["border", "cellpadding", "cellspacing"],
        },
        strip=True,
        css_sanitizer=CSSSanitizer(
            allowed_css_properties=[*ALLOWED_CSS_PROPERTIES, "margin-left", "margin-right"]
        ),
    )
    return value


class SanitizedStr(str):
    """
    A self-sanitizing string type for Pydantic models,
    using sanitize_string on instantiation.
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type, handler: GetCoreSchemaHandler
    ) -> pydantic_core.CoreSchema:
        return pydantic_core.core_schema.no_info_after_validator_function(
            sanitize_string,
            pydantic_core.core_schema.str_schema(),
            serialization=pydantic_core.core_schema.str_schema(),
        )


SanitizedField = Annotated[SanitizedStr, Field()]


def get_model_aliases(model: Type[BaseModel]) -> dict:
    """
    Returns a dictionary of field aliases for the given model.

    Args:
        model: The model class for which to retrieve the field aliases.

    Returns:
        A dictionary where the keys are the field names and the values are the field aliases.
    """
    return {
        name: field.alias for name, field in model.model_fields.items() if field.alias is not None
    }


def validate_with(model: Type[BaseModel]):
    """
    Decorator function that validates the input data using the provided model.

    Args:
        model: The model to validate the input data against.

    Returns:
        The decorated function that performs the validation.

    Raises:
        ValidationError: If the input data fails validation.
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                # Get aliases before validation to handle incoming data
                aliases = get_model_aliases(model)

                # Replace aliased keys in the incoming data
                input_data = {aliases.get(k, k): v for k, v in request.json.items()}

                # Convert empty strings to None
                input_data = convert_empty_strings_to_none(input_data)

                # Validate the data
                validated_data = model(**input_data).model_dump(exclude_unset=True, by_alias=True)

                # Convert back to original field names for the output
                reversed_aliases = {v: k for k, v in aliases.items()}
                output_data = {reversed_aliases.get(k, k): v for k, v in validated_data.items()}

            except ValidationError as e:
                formatted_errors = format_validation_errors(e.errors())
                return {"message": "Validation failed", "errors": formatted_errors}, 400
            return f(*args, validated_data=output_data, **kwargs)

        return wrapper

    return decorator


def format_validation_errors(errors: list) -> dict:
    """
    Formats the validation errors into a dictionary.

    Args:
        errors: A list of validation errors.

    Returns:
        A dictionary containing the formatted validation errors, where the keys are the field names and the values are the error messages.
    """
    formatted_errors = {}
    for error in errors:
        loc = error["loc"]
        field = ".".join(str(e) for e in loc)  # Handle nested fields
        msg = error["msg"]
        type_ = error.get("type")

        if type_ == "extra_forbidden":
            formatted_errors[field] = "Extra field not allowed"
        elif type_ == "missing":
            formatted_errors[field] = "Required field not provided"
        elif type_ == "type_error":
            formatted_errors[field] = "Wrong type for field"
        else:
            formatted_errors[field] = f"Invalid value for field: {msg}"

    return formatted_errors


def one_must_exist(field_names: list[str], strict=False) -> Type[BaseModel]:
    """
    Returns a dynamically created Pydantic model that enforces the condition that at least one of the specified field names
    must be provided and not empty.

    Args:
        - field_names: A list of field names to check.
        - strict: If set to True, only the specified field names will be allowed in the model. Defaults to False.

    Returns:
        - A dynamically created Pydantic model that enforces the condition.

    Raises:
        - ValueError: If none of the specified field names are provided or all of them are empty.
    """

    class Model(BaseModel):
        model_config = ConfigDict(extra="forbid" if strict else "allow", str_strip_whitespace=True)

        @model_validator(mode="before")
        @classmethod
        def check_values(cls, data: dict) -> dict:
            if not any(data.get(field_name) for field_name in field_names if field_name in data):
                raise ValueError(f"At least one of {field_names} must be provided and not empty.")
            return data

    return Model


def convert_empty_strings_to_none(data: Any) -> Any:
    """
    Recursively convert empty strings in a data structure to None.

    Args:
        - data: The data structure to convert.

    Returns:
        - The data structure with empty strings converted to None.
    """
    if isinstance(data, dict):
        return {k: convert_empty_strings_to_none(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_empty_strings_to_none(item) for item in data]
    elif isinstance(data, str) and data == "":
        return None
    else:
        return data
