import os
import tempfile
import json
import pandas as pd
from typing import Any, Generator
from flask import current_app
import pytest
from enferno.utils.logging_utils import get_logger
import enferno.utils.typing as t

logger = get_logger()


# utility function to get first record of entity or fail
def get_first_or_fail(entity: t.Model) -> t.Model:
    """
    Get the first record of an entity or raise an exception if no records are found.

    Args:
        - entity: The entity to query.

    Raises:
        - Exception: If no records are found in the entity.

    Returns:
        - The first record of the entity.
    """
    ent = entity.query.first()
    if not ent:
        raise Exception(f"No {entity.__name__} in db to test against")
    return ent


# utility function to coerce data into schema or fail
def conform_to_schema_or_fail(data: Any, schema: Any) -> None:
    """
    Test if data conforms to a schema or raise an exception if it does not.

    Args:
        - data: The data to test.
        - schema: The schema to test against.

    Raises:
        - AssertionError: If the data does not conform to the schema.

    Returns:
        None
    """
    try:
        _ = schema(**data)
    except Exception as e:
        pytest.fail(f"Response does not conform to schema, {e}")


# utility generator function for CSVs
def create_csv_for_entities(entities: list, headers: list) -> Generator[str, Any, None]:
    """
    Generator function to create and yield a temporary CSV file with a specified header and entities.

    Args:
        - entities: A list of entities to write to the CSV.
        - headers: A list of headers for the CSV.

    Yields:
        - The path to the temporary CSV file.
    """
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".csv") as tmp:
        tmp.write(",".join(headers) + "\n")
        for entity in entities:
            row = [
                str(getattr(entity, field) if getattr(entity, field) is not None else "")
                for field in headers
            ]
            tmp.write(",".join(row) + "\n")
        tmp.seek(0)
        yield tmp.name
    os.unlink(tmp.name)


# utility generator function for binaries
def create_binary_file(extension, content=b"Test content"):
    """
    Generator function to create and yield a temporary binary file with a specified extension and content.

    Args:
        - extension: The file extension for the temporary file.
        - content: Binary content to write to the file. Defaults to b'Test content'.

    Yields:
        - The path to the temporary file.
    """
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix="." + extension) as tmp:
        tmp.write(content)
        tmp.flush()  # Ensure all data is written to disk
        yield tmp.name  # Yield the path to the temporary file for use in tests

    os.unlink(tmp.name)  # Cleanup: remove the temporary file after the test


# utility generator function for temp xls
def create_xls_file(content={}):
    """
    Generator function to create and yield a temporary xls file.

    Args:
        content (dict): The content to write to the file.

    Yields:
        str: The path to the temporary file.
    """
    df = pd.DataFrame(content)
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xlsx") as tmp:
        df.to_excel(tmp.name, index=False)
        tmp.flush()  # Ensure all data is written to disk
        yield tmp.name  # Yield the path to the temporary file for use in tests

    os.unlink(tmp.name)  # Cleanup: remove the temporary file after the test


def get_uid_from_client(users: list, client_fixture: str) -> t.id:
    """
    Get the user id of the test user associated with the client fixture.

    Args:
        - users: A list of users to query.
        - client_fixture: The client fixture to query.

    Returns:
        - The user id from the client fixture.
    """
    admin_user, da_user, mod_user, _ = users
    uid = None
    if client_fixture == "admin_client":
        uid = admin_user.id
    elif client_fixture == "da_client":
        uid = da_user.id
    elif client_fixture == "mod_client":
        uid = mod_user.id
    return uid
