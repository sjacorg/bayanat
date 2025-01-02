from typing import Union, get_args, get_origin
from pydantic import BaseModel, ConfigDict, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BaseResponseModel(StrictModel):
    @model_validator(mode="before")
    @classmethod
    def validate_items(cls, values):
        items_type = cls.model_fields.get("items")
        if not items_type:
            raise ValueError("The 'items' field is not defined in the subclass.")

        items = values.get("items", [])
        if not isinstance(items, list):
            raise ValueError("'items' must be a list")

        # Get the type of items
        items_type = items_type.annotation

        if get_origin(items_type) is list:
            # Extract the type inside the List (which should be a Union)
            union_type = get_args(items_type)[0]
            # Now check if this type is a Union
            if get_origin(union_type) is Union:
                models = get_args(union_type)
            else:
                # Handle the case where the List does not contain a Union
                models = [union_type]
        else:
            # Handle non-List types if necessary
            models = [items_type]

        validated_items = []

        for v in items:
            item_validated = False
            for model in models:
                try:
                    validated_item = model.model_validate(v)
                    validated_items.append(validated_item)
                    item_validated = True
                    break
                except ValueError:
                    continue

            if not item_validated:
                raise ValueError(f"None of the models match for item: {v}")

        values["items"] = validated_items  # Replace the original list with validated items
        return values
