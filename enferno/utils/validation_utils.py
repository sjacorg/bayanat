import re
import unicodedata
from html import unescape
from email_validator import validate_email, EmailNotValidError
from zxcvbn import zxcvbn
from functools import wraps
from typing import Any, Type, Annotated
from flask import request
from enum import Enum
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


def validate_no_html(data: str) -> None:
    if not data.strip():
        return data
    # Reject HTML tags
    if re.search(r"<[^>]*>", data):
        raise WTFormsValidationError(f"HTML tags are not allowed.")

    # Reject HTML entities
    if unescape(data) != data:
        raise WTFormsValidationError(f"HTML entities are not allowed.")


def validate_username(username: str) -> None:
    """
    Validates a username.
    """
    # validate length
    if not username or not username.strip():
        raise WTFormsValidationError(f"Username cannot be empty.")
    if len(username) > 32:
        raise WTFormsValidationError(f"Username is too long (maximum 32 characters).")
    # validate no html
    validate_no_html(username)
    # validate no whitespace
    if username != username.strip():
        raise WTFormsValidationError(f"Username cannot contain leading or trailing whitespace.")
    # validate no special characters
    if not re.match(r"^[a-zA-Z0-9]+$", username):
        raise WTFormsValidationError(f"Username can only contain letters and numbers.")


def validate_username_constraints(username: str) -> str:
    """
    Centralized username validation logic - equivalent to original validation but simplified.

    Args:
        username: The username to validate

    Returns:
        str: The validated username

    Raises:
        ValueError: If username format is invalid
    """
    # Handle empty/None - equivalent to original
    if not username or not username.strip():
        raise ValueError("Username cannot be empty")

    # Length validation (centralized constants) - equivalent to original Field(min_length=4, max_length=32)
    MIN_LENGTH = 4  # From Field(min_length=4)
    MAX_LENGTH = 32

    if len(username) < MIN_LENGTH:
        raise ValueError("String should have at least 4 characters")

    if len(username) > MAX_LENGTH:
        raise ValueError("Username is too long (maximum 32 characters)")

    # HTML validation - equivalent to original validate_no_html()
    if re.search(r"<[^>]*>", username):
        raise ValueError("HTML tags are not allowed")

    from html import unescape

    if unescape(username) != username:
        raise ValueError("HTML entities are not allowed")

    # Whitespace validation - equivalent to original
    if username != username.strip():
        raise ValueError("Username cannot contain leading or trailing whitespace")

    # Character validation - equivalent to original ^[a-zA-Z0-9]+$ (no underscore/hyphen)
    if not re.match(r"^[a-zA-Z0-9]+$", username):
        raise ValueError("Username can only contain letters and numbers")

    return username


def validate_webauthn_device_name(name: str) -> str:
    """
    Validates a webauthn device name and returns a normalized version of it.
    """
    if not name or not name.strip():
        raise WTFormsValidationError(f"Webauthn device name cannot be empty.")
    # validate no html
    validate_no_html(name)

    # normalize whitespace
    name = " ".join(name.split())
    # validate length
    if len(name) > 64:
        raise WTFormsValidationError(f"Webauthn device name is too long (maximum 64 characters).")
    # allow unicode L, N, whitespace, _ and -
    for char in name:
        if char not in {"-", "_", " "} and unicodedata.category(char)[0] not in {"L", "N"}:
            raise WTFormsValidationError(
                f"Webauthn device name can only contain letters, numbers, underscores, and hyphens."
            )
    return name


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
        raise WTFormsValidationError("Email cannot be empty.")

    try:
        # Use email-validator library for unicode/IDN support
        validated_email = validate_email(email.strip(), check_deliverability=False)
        return validated_email
    except EmailNotValidError as e:
        raise WTFormsValidationError(f"Invalid email format: {str(e)}")


def validate_password_zxcvbn(password: str, minimum_score: int = 3) -> tuple[bool, int]:
    """
    Validates a password using zxcvbn.
    """
    result = zxcvbn(password)
    score = result.get("score")
    return score >= minimum_score, score


def validate_password_policy(p: str) -> str:
    from enferno.settings import Config

    if not (p := p.strip()):
        raise ValueError("Password cannot be empty!")

    # Use smart config getter that handles app context automatically
    min_length = Config.get("SECURITY_PASSWORD_LENGTH_MIN")
    complexity_checker = Config.get("SECURITY_PASSWORD_COMPLEXITY_CHECKER", "zxcvbn")
    min_score = Config.get("SECURITY_ZXCVBN_MINIMUM_SCORE")

    # validate length
    if len(p) < min_length:
        raise ValueError(f"Password should be at least {min_length} characters long!")

    if complexity_checker.lower() == "zxcvbn":
        # validate complexity using zxcvbn
        valid, score = validate_password_zxcvbn(p, min_score)
        if not valid:
            raise ValueError(
                f"Password is too weak (score: {score} < {min_score}). Please use a stronger password."
            )
    return p


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


# =============================================================================
# Dynamic Field Type Validation
# =============================================================================


class FieldType(str, Enum):
    """Supported field types for dynamic field validation."""

    TEXT = "text"
    LONG_TEXT = "long_text"
    NUMBER = "number"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    SELECT = "select"
