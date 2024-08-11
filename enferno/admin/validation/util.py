from functools import wraps
from typing import List, Type
from flask import request
from pydantic import BaseModel, Field, ValidationError, root_validator
import bleach
import enferno.utils.typing as t
from bleach.css_sanitizer import CSSSanitizer, ALLOWED_CSS_PROPERTIES


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


def sanitize():
    return Field(default=None, sa_field_validate=sanitize_string)


def get_model_aliases(model: t.Model) -> dict:
    """
    Returns a dictionary of field aliases for the given model.

    Args:
        model: The model object for which to retrieve the field aliases.

    Returns:
        A dictionary where the keys are the field aliases and the values are the field names.

    """
    return {field.alias: name for name, field in model.__fields__.items() if field.has_alias}


# decorator function to validate incoming payload with specified pydantic validation
def validate_with(model: t.Model):
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
                validated_data = model(**request.json).dict(exclude_unset=True)
                aliases = get_model_aliases(model)
                reversed_aliases = {v: k for k, v in aliases.items()}
                output_data = {reversed_aliases.get(k, k): v for k, v in validated_data.items()}
            except ValidationError as e:
                formatted_errors = format_validation_errors(e.errors())
                return {"message": "Validation failed", "errors": formatted_errors}, 400
            return f(*args, validated_data=dict(output_data), **kwargs)

        return wrapper

    return decorator


# Function to extract and format validation errors
def format_validation_errors(errors: list) -> dict:
    """
    Formats the validation errors into a dictionary.

    Args:
        - errors: A list of validation errors.

    Returns:
        - A dictionary containing the formatted validation errors, where the keys are the field names and the values are the error messages.
    """
    formatted_errors = {}
    for error in errors:
        loc = error["loc"]
        field = ".".join(str(e) for e in loc)  # Handle nested fields
        msg = error["msg"]

        if "extra fields not permitted" in msg:
            formatted_errors[field] = f"Extra field not allowed"
        elif "field required" in msg:
            formatted_errors[field] = f"Required field not provided"
        elif "type error" in msg:
            formatted_errors[field] = f"Wrong type for field"
        else:
            formatted_errors[field] = f"Invalid value for field: {msg}"

    return formatted_errors


def one_must_exist(field_names: List[str], strict=False) -> Type[BaseModel]:
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
        class Config:
            anystr_strip_whitespace = True
            extra = "forbid" if strict else "allow"

        @root_validator(pre=True, allow_reuse=True)
        def check_values(cls, values):
            if not any(
                values.get(field_name) for field_name in field_names if field_name in values
            ):
                raise ValueError(f"At least one of {field_names} must be provided and not empty.")
            return values

    return Model
