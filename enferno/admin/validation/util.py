from functools import wraps
from typing import Type, Annotated
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

                # Validate the data
                validated_data = model(**input_data).model_dump(exclude_unset=True)

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
