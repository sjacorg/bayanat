# -*- coding: utf-8 -*-
"""Click commands."""
import os

import arrow
from datetime import timedelta
import click
from flask.cli import AppGroup
from flask.cli import with_appcontext
from flask_security.utils import hash_password

from enferno.settings import Config
from enferno.extensions import db
from enferno.user.models import User, Role
from enferno.utils.config_utils import ConfigManager
from enferno.utils.data_helpers import (
    import_default_data,
    generate_user_roles,
    generate_workflow_statues,
    create_default_location_data,
    media_check_duplicates,
)
from enferno.utils.db_alignment_helpers import DBAlignmentChecker
from enferno.utils.logging_utils import get_logger
from sqlalchemy import text

logger = get_logger()


@click.command()
@click.option("--create-exts", is_flag=True)
@with_appcontext
def create_db(create_exts: bool) -> None:
    """
    Creates db tables - import your models within commands.py to create the models.

    Args:
        - create_exts: bool - create db extensions

    Returns:
        None
    """
    logger.info("Creating database structure")
    # create db exts if required, needs superuser db permissions
    if create_exts:
        with db.engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION if not exists pg_trgm ;"))
            click.echo("Trigram extension installed successfully")
            conn.execute(text("CREATE EXTENSION if not exists postgis ;"))
            click.echo("Postgis extension installed successfully")
            conn.commit()

    db.create_all()
    click.echo("Database structure created successfully")
    logger.info("Database structure created successfully")
    generate_user_roles()
    click.echo("Generated user roles successfully.")
    logger.info("Generated user roles successfully.")
    generate_workflow_statues()
    click.echo("Generated system workflow statues successfully.")
    logger.info("Generated system workflow statues successfully.")
    create_default_location_data()
    click.echo("Generated location metadata successfully.")
    logger.info("Generated location metadata successfully.")


@click.command()
@with_appcontext
def import_data() -> None:
    """
    Imports default Bayanat data for lists and relationship types.
    """
    logger.info("Importing data.")
    try:
        import_default_data()
        click.echo("Imported data successfully.")
        logger.info("Imported data successfully.")
    except:
        click.echo("Error importing data.")
        logger.error("Error importing data.")


@click.command()
@with_appcontext
def install() -> None:
    """Install a default Admin user and add an Admin role to it."""
    logger.info("Installing admin user.")
    admin_role = Role.query.filter(Role.name == "Admin").first()

    # check if there's an existing admin
    if admin_role.users.all():
        click.echo("An admin user is already installed.")
        logger.error("An admin user is already installed.")
        return

    # to make sure username doesn't already exist
    while True:
        u = click.prompt("Admin username?", default="admin")
        check = User.query.filter(User.username == u.lower()).first()
        if check is not None:
            click.echo("Username already exists.")
        else:
            break

    p = click.prompt("Admin Password?", hide_input=True)
    user = User(username=u, password=hash_password(p), active=1)
    user.name = "Admin"
    user.roles.append(admin_role)
    check = user.save()
    if check:
        click.echo("Admin user installed successfully.")
        logger.info("Admin user installed successfully.")
    else:
        click.echo("Error installing admin user.")
        logger.error("Error installing admin user.")


@click.command()
@click.option("-u", "--username", prompt=True, default=None)
@click.option("-p", "--password", prompt=True, default=None, hide_input=True)
@with_appcontext
def create(username: str, password: str) -> None:
    """
    Creates a user.

    Args:
        - username: str - username
        - password: str - password

    Returns:
        None
    """
    logger.info("Creating user: {}".format(username))
    if len(username) < 4:
        click.echo("Username must be at least 4 characters long")
        return
    user = User.query.filter(User.username == username).first()
    if user:
        click.echo("User already exists!")
        logger.error("User already exists!")
        return
    if len(password) < 8:
        click.echo("Password should be at least 8 characters long!")
        logger.error("Password should be at least 8 characters long!")
        return
    user = User(username=username, password=hash_password(password), active=1)
    if user.save():
        click.echo("User created successfully")
        logger.info("User created successfully")
    else:
        click.echo("Error creating user.")
        logger.error("Error creating user.")


@click.command()
@click.option("-u", "--username", prompt=True, default=None)
@click.option("-r", "--role", prompt=True, default="Admin")
@with_appcontext
def add_role(username: str, role: str) -> None:
    """
    Adds a role to the specified user.

    Args:
        - username: str - username
        - role: str - role

    Returns:
        None
    """
    logger.info("Adding role {} to user {}".format(role, username))
    from enferno.user.models import Role

    user = User.query.filter(User.username == username).first()

    if not user:
        click.echo("Sorry, this user does not exist!")
        logger.error("User does not exist.")
    else:
        r = Role.query.filter(Role.name == role).first()
        if not role:
            click.echo("Sorry, this role does not exist!")
            u = click.prompt("Would you like to create one? Y/N", default="N")
            if u.lower() == "y":
                r = Role(name=role).save()
        # add role to user
        user.roles.append(r)
        click.echo("Role {} added successfully to user {}".format(username, role))
        logger.info("Role {} added successfully to user {}".format(username, role))


@click.command()
@click.option("-u", "--username", prompt=True, default=None)
@click.option(
    "-p", "--password", hide_input=True, confirmation_prompt=True, prompt=True, default=None
)
@with_appcontext
def reset(username: str, password: str) -> None:
    """
    Reset a user password.

    Args:
        - username: str - username
        - password: str - password

    Returns:
        None
    """
    logger.info("Resetting password for user: {}".format(username))
    user = User.query.filter(User.username == username).first()
    if not user:
        click.echo("Specified user does not exist!")
        logger.error("Specified user does not exist!")
    else:
        if len(password) < 8:
            click.echo("Password should be at least 8 characters long!")
            logger.error("Password should be at least 8 characters long!")
            return
        user.password = hash_password(password)
        user.save()
        click.echo("User password has been reset successfully.")
        logger.info("User password has been reset successfully.")
        if not user.active:
            click.echo("Warning: User is not active!")
            logger.warning("User is not active!")


@click.command()
def clean() -> None:
    """Remove *.pyc and *.pyo files recursively starting at current directory.
    Borrowed from Flask-Script, converted to use Click.
    """
    logger.info("Cleaning *.pyc and *.pyo files.")
    for dirpath, dirnames, filenames in os.walk("."):
        for filename in filenames:
            if filename.endswith(".pyc") or filename.endswith(".pyo"):
                full_pathname = os.path.join(dirpath, filename)
                click.echo("Removing {}".format(full_pathname))
                os.remove(full_pathname)


# translation management
i18n_cli = AppGroup("translate", short_help="commands to help with translation management")


@i18n_cli.command()
def extract() -> None:
    """
    Extracts all translatable strings from the project.

    Raises:
        - RuntimeError: Extract command failed

    Returns:
        None
    """
    logger.info("Extracting translatable strings.")
    if os.system("pybabel extract -F babel.cfg -k _l -o messages.pot ."):
        logger.error("Extract command failed")
        raise RuntimeError("Extract command failed")


@i18n_cli.command()
def update() -> None:
    """
    Updates the translations.

    Raises:
        - RuntimeError: Update command failed

    Returns:
        None
    """
    logger.info("Updating translations.")
    if os.system("pybabel update -i messages.pot -d enferno/translations"):
        logger.error("Update command failed")
        raise RuntimeError("Update command failed")


@i18n_cli.command()
def compile() -> None:
    """
    Compiles the translations.

    Raises:
        - RuntimeError: Compile command failed

    Returns:
        None
    """
    logger.info("Compiling translations.")
    if os.system("pybabel compile -d enferno/translations"):
        logger.error("Compile command failed")
        raise RuntimeError("Compile command failed")


# Database Schema Alignment
@click.command()
@with_appcontext
def check_db_alignment() -> None:
    """Check the alignment of the database schema with the models."""
    logger.info("Checking database schema alignment.")
    checker = DBAlignmentChecker()
    checker.check_db_alignment()
    logger.info("Database schema alignment check completed.")


@click.command()
@with_appcontext
def generate_config() -> None:
    """Restore the default configuration."""
    # Check if a config file exists
    if os.path.exists(ConfigManager.CONFIG_FILE_PATH):
        verify = click.prompt("A config file already exists. Overwrite? (y/N)", default="n")
        if verify.lower() != "y":
            click.echo("Config file not overwritten.")
            return
    logger.info("Restoring default configuration.")
    ConfigManager.restore_default_config()


# ------------------ ETL DOCS --------------------------- #
from enferno.data_import.models import DataImport


@click.command()
@with_appcontext
@click.argument("file")
def import_docs(file) -> None:
    """Import the docs."""
    click.echo("Importing docs.")
    from enferno.data_import.utils.docs_import import DocImport
    from enferno.tasks import process_doc

    import pandas as pd
    import shortuuid

    df = pd.read_csv(file)
    files = df.to_dict(orient="records")

    batch_id = shortuuid.uuid()[:9]

    with click.progressbar(files, label="Importing docs", show_pos=True) as bar:
        for item in bar:
            meta = {
                "sha256": item["sha256"],
            }

            file_path = item["file_path"]
            if not (
                file_path.endswith(".jpg")
                or file_path.endswith(".pdf")
                or file_path.endswith(".png")
            ):
                click.echo(f"Skipping file {file_path}")
                continue

            data_import = DataImport(
                user_id=1,
                table="bulletin",
                file=file_path,
                batch_id=batch_id,
                data={
                    "mode": 0,  # custom mode
                },
            )

            data_import.add_to_log(f"Added file {item} to import queue.")
            data_import.save()

            process_doc.delay(
                batch_id=batch_id,
                file_path=file_path,
                meta=meta,
                user_id=1,
                data_import_id=data_import.id,
            )

        click.echo("=== Done ===")


# ------------------ YouTube ETL --------------------------- #

import os
import pandas as pd
import shortuuid
from enferno.tasks import process_etl


@click.command()
@with_appcontext
@click.argument("file")
@with_appcontext
def import_youtube(file):
    """
    Runs the YouTube ETL pipeline
    :param file: text file contains youtube ids, each id on a separate line
    :return: success/error logs
    """
    batch_id = shortuuid.uuid()[:9]

    if not os.path.isfile(file):
        print("Invalid file!")
        return

    csv_file = pd.read_csv(file)
    files = csv_file.to_dict(orient="records")

    with click.progressbar(files, label="Importing videos", show_pos=True) as bar:
        for line in bar:
            try:
                meta = {
                    "bucket": line["bucket"],
                    "meta_file": line["file"],
                    "video_file": line["file"].replace(".info.json", ".mp4"),
                    "checksum_file": line["file"].replace(".info.json", ".checksum"),
                    "id": line["id"],
                    "mode": 3,
                }
                # Create import log
                data_import = DataImport(
                    user_id=1,
                    table="bulletin",
                    file=line["file"],
                    batch_id=batch_id,
                    file_format="mp4",
                    data={
                        "mode": 3,  # Web import mode
                        "optimize": False,
                        "sources": [],
                        "labels": [],
                        "ver_labels": [],
                        "locations": [],
                        "tags": [],
                        "roles": [],
                    },
                )

                data_import.add_to_log(f"Started processing {line["file"]}")
                data_import.save()

                process_etl.delay(batch_id=batch_id, meta=meta, data_import_id=data_import.id)
            except Exception as e:
                click.echo(e)


import json
import boto3


from enferno.tasks import process_telegram_media
from enferno.data_import.utils.telegram_utils import parse_html_messages


@click.command()
@with_appcontext
@click.argument("bucket")
@click.argument("folder")
def import_telegram(bucket, folder):

    s3 = boto3.client(
        "s3",
        aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
        region_name=Config.AWS_REGION,
    )

    if not folder.endswith("/"):
        folder += "/"

    objects = s3.list_objects_v2(
        Bucket=bucket,
        Prefix=folder,
        Delimiter="/",
    )

    channels = []
    for prefix in objects.get("CommonPrefixes", []):
        channels.append(prefix["Prefix"].split("/")[-2])

    batch_id = shortuuid.uuid()[:9]

    with click.progressbar(channels, label="Processing Telegram Channels", show_pos=True) as cbar:
        for channel in cbar:
            # get meta file
            meta_file = s3.get_object(
                Bucket=bucket,
                Key=folder + channel + "/meta.json",
            )

            # read the file
            meta_file = meta_file["Body"].read().decode("utf-8")
            meta_file = json.loads(meta_file)

            click.echo(f"Downloading channel {channel} meta file")
            try:
                messages_file = s3.get_object(
                    Bucket=bucket,
                    Key=folder + channel + "/messages.json",
                )

                messages = messages_file["Body"].read().decode("utf-8")
                messages = json.loads(messages)

            except Exception as e:
                click.echo(f"Channel {channel} has no messages JSON file... Looking for HTML file")

                try:
                    messages_file = s3.get_object(
                        Bucket=bucket,
                        Key=folder + channel + "/messages.html",
                    )
                    html = messages_file["Body"].read().decode("utf-8")
                    
                    messages = parse_html_messages(html)
                    click.echo(f"Parsed {len(messages)} messages from HTML file")

                except Exception as e:
                    click.echo(f"Channel {channel} has no messages HTML file... Skipping")
                    continue
                
            # preprocess to link media 
            processed_messages = []
            temp_group = []
            click.echo(f"Processing channel {channel}")
            for i, message in enumerate(messages):
                date = arrow.get(message["date"]).datetime
                if temp_group:
                    # check if the last message in the group is more than 2 second old
                    old_date = arrow.get(temp_group[-1]["date"]).datetime
                    if date - old_date > timedelta(seconds=2):
                        # if the difference is more than 2 second, it's a new group
                        processed_messages.append(temp_group)
                        temp_group = []

                if not message.get("text") and message.get("media_path"):
                    # media and no text implies it's linked to a previous message
                    # append the last message to the group
                    temp_group.append(message)
                elif message.get("text") and message.get("media_path"):
                    # end of the threat
                    # append the last message and push the group
                    temp_group.append(message)
                    processed_messages.append(temp_group)
                    temp_group = []
                # drop text only messages

            with click.progressbar(
                processed_messages, label="Processing Telegram Channels", show_pos=True
            ) as mbar:
                for messages in mbar:
                    try:
                        data_imports = []
                        main_id = None
                        messages.reverse()
                        
                        for message in messages:
                            data = {
                                "mode": 4,  # Telegram import mode
                                "bucket": bucket,
                                "folder": folder,
                                "main": main_id,
                                "info": {
                                    "message": message,
                                    "channel_metadata": meta_file,
                                },
                            }

                            file_path = f"{bucket}/{folder}{channel}/{message['media_path']}"

                            data_import = DataImport(
                                user_id=1,
                                table="bulletin",
                                file=file_path,
                                batch_id=batch_id,
                                data=data,
                            )

                            data_import.add_to_log(
                                f"Started processing message {message.get('id')}"
                            )
                            data_import.save()

                            # add the first message as the main message
                            # and the rest as linked messages
                            if main_id is None:
                                main_id = data_import.id
                            
                            data_imports.append(data_import.id)

                        process_telegram_media.delay(
                            data_imports=data_imports,
                        )

                    except Exception as e:
                        click.echo(f"Error processing message {messages[-1].get('id')}: {e}")
