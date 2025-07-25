import re
from html import unescape
from zxcvbn import zxcvbn
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
        raise WTFormsValidationError(f"{field_name} is too long (maximum {max_length} characters).")


def validate_password_zxcvbn(password: str, minimum_score: int = 3) -> tuple[bool, int]:
    """
    Validates a password using zxcvbn.
    """
    result = zxcvbn(password)
    score = result.get("score")
    return score >= minimum_score, score


def validate_password_policy(p: str) -> str:
    from enferno.settings import Config as cfg

    if not (p := p.strip()):
        raise ValueError("Password cannot be empty!")
    # validate length
    min_length = getattr(cfg, "SECURITY_PASSWORD_LENGTH_MIN")
    if len(p) < min_length:
        raise ValueError(f"Password should be at least {min_length} characters long!")

    if getattr(cfg, "SECURITY_PASSWORD_COMPLEXITY_CHECKER", "zxcvbn").lower() == "zxcvbn":
        # validate complexity using zxcvbn
        min_score = getattr(cfg, "SECURITY_ZXCVBN_MINIMUM_SCORE", 3)
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
