from typing import List, Union, get_args, get_origin
from pydantic import BaseModel, ValidationError, root_validator


class StrictModel(BaseModel):
    class Config:
        extra = "forbid"
        # allow_population_by_field_name = True


class BaseResponseModel(StrictModel):
    @root_validator(pre=True)
    def validate_items(cls, values):
        items_type = cls.__annotations__.get("items")
        if not items_type:
            raise ValueError("The 'items' field is not defined in the subclass.")

        if get_origin(items_type) is list or get_origin(items_type) is List:
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

        for v in values.get("items", []):
            item_validated = False
            for model in models:
                try:
                    validated_item = model(**v)
                    validated_items.append(validated_item)
                    item_validated = True
                    break
                except ValidationError:
                    continue

            if not item_validated:
                raise ValueError(f"None of the models match for item: {v}")

        values["items"] = validated_items  # Replace the original list with validated items
        return values
