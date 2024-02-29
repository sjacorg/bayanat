import os
import tempfile
import json
import pytest


# if the content-type: application/json header is missing, use json.loads to parse the
# plaintext response into json
def load_data(response):
    if response.json is None and response.text:
        try:
            json_data = json.loads(response.text)
        except json.JSONDecodeError as e:
            print("Response is not in valid JSON format", e)
            return None
    else:
        json_data = response.json
    return json_data


# utility function to recursively set empty strings to None
def convert_empty_strings_to_none(data):
    if isinstance(data, dict):
        return {k: convert_empty_strings_to_none(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_empty_strings_to_none(item) for item in data]
    elif isinstance(data, str) and data == "":
        return None
    else:
        return data


# utility function to get first record of entity or fail
def get_first_or_fail(entity):
    ent = entity.query.first()
    if not ent:
        raise Exception(f"No {entity.__name__} in db to test against")
    return ent


# utility function to coerce data into schema or fail
def conform_to_schema_or_fail(data, schema):
    try:
        _ = schema(**data)
    except Exception as e:
        pytest.fail(f"Response does not conform to schema, {e}")


# utility generator function for CSVs
def create_csv_for_entities(entities, headers):
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
        extension (str): The file extension for the temporary file.
        content (bytes): Binary content to write to the file. Defaults to b'Test content'.

    Yields:
        str: The path to the temporary file.
    """
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix="." + extension) as tmp:
        tmp.write(content)
        tmp.flush()  # Ensure all data is written to disk
        yield tmp.name  # Yield the path to the temporary file for use in tests

    os.unlink(tmp.name)  # Cleanup: remove the temporary file after the test


def get_uid_from_client(users, client_fixture):
    admin_user, da_user, mod_user, _ = users
    uid = None
    if client_fixture == "admin_client":
        uid = admin_user.id
    elif client_fixture == "da_client":
        uid = da_user.id
    elif client_fixture == "mod_client":
        uid = mod_user.id
    return uid
