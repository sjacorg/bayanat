from typing import Iterable, Optional


def convert_list_attributes(dictionary: dict) -> dict:
    """
    convert dictionary list attributes into named attributes based on their index.

    Args:
        - dictionary: input dict

    Returns:
        - dictionary: dictionary with named attributes in place of list attributes
    """
    keys = list(dictionary.keys())  # Create a copy of the dictionary keys
    for key in keys:
        value = dictionary[key]
        if isinstance(value, list):
            for index, item in enumerate(value):
                dictionary[f"{key} {index}"] = item
            del dictionary[key]
        elif isinstance(value, dict):
            convert_list_attributes(value)
    return dictionary


def convert_simple_relation(relation: Iterable) -> Optional[dict]:
    """
    Convert a simple relation to a dictionary.

    Args:
        - relation (Iterable): The relation to convert.

    Returns:
        - dict: The converted relation as a dictionary.
    """
    output = {}
    if relation:
        for i, v in enumerate(relation):
            output[f"{v.__tablename__}-{i + 1}"] = f"{v.id}-{v.title}"
        return output
    return None


def convert_complex_relation(relation: Iterable, table_name: str) -> Optional[dict]:
    """
    Convert a complex relation to a dictionary.

    Args:
        - relation (Iterable): The relation to convert.
        - table_name (str): The name of the table.

    Returns:
        - dict: The converted relation as a dictionary.
    """
    output = {}
    if relation:
        for i, v in enumerate(relation):
            if table_name in ["bulletin", "incident"]:
                output[
                    f"{table_name}-{i + 1}"
                ] = f'{v.get(f"{table_name}").get("id")}-{v.get(f"{table_name}").get("title")}'
            elif table_name == "actor":
                output[
                    f"{table_name}-{i + 1}"
                ] = f'{v.get(f"{table_name}").get("id")}-{v.get(f"{table_name}").get("name")}'
        return output
    return None
