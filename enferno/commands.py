# -*- coding: utf-8 -*-
"""Click commands."""
import os
from datetime import datetime, timezone

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
)
from enferno.utils.db_alignment_helpers import DBAlignmentChecker
from enferno.utils.logging_utils import get_logger
from sqlalchemy import text
from enferno.admin.models import Bulletin
from enferno.admin.models.DynamicField import DynamicField
from enferno.admin.models.DynamicFormHistory import DynamicFormHistory
from enferno.utils.date_helper import DateHelper
from enferno.utils.form_history_utils import record_form_history

from enferno.utils.validation_utils import validate_password_policy

logger = get_logger()


def create_initial_snapshots():
    """Create initial form history snapshots for all entity types."""
    for entity_type in ["bulletin", "incident", "actor"]:
        existing = DynamicFormHistory.query.filter_by(entity_type=entity_type).first()
        if not existing:
            record_form_history(entity_type, user_id=None)
            logger.info(f"Created initial snapshot for {entity_type}")


def generate_core_fields():
    """Generate core fields and create initial form history snapshots."""
    from enferno.admin.models.core_fields import seed_core_fields

    logger.info("Seeding core fields...")
    seed_core_fields()
    create_initial_snapshots()
    logger.info("Core fields seeded successfully")


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
    generate_core_fields()
    click.echo("Generated core fields successfully.")
    logger.info("Generated core fields successfully.")


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
    while True:
        p = click.prompt("Admin Password?", hide_input=True)
        try:
            p = validate_password_policy(p)
            break
        except ValueError as e:
            click.echo(str(e))
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
    try:
        password = validate_password_policy(password)
    except ValueError as e:
        click.echo(str(e))
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
        try:
            password = validate_password_policy(password)
        except ValueError as e:
            click.echo(str(e))
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


# OCR text extraction commands
ocr_cli = AppGroup("ocr", short_help="OCR text extraction commands")


@ocr_cli.command()
@click.option("--media-id", "-m", required=True, type=int, help="Media ID to extract text from")
@click.option(
    "--language",
    "-l",
    multiple=True,
    default=["ar", "en"],
    help="Language hints (can specify multiple)",
)
@click.option("--show-text", "-t", is_flag=True, help="Print extracted text")
@with_appcontext
def extract(media_id: int, language: tuple, show_text: bool) -> None:
    """Extract text from a media file using Google Vision OCR."""
    from enferno.admin.models import Extraction
    from enferno.tasks.extraction import process_media_extraction_task

    click.echo(f"Extracting text from media {media_id}...")
    result = process_media_extraction_task(media_id, list(language))

    if result.get("success"):
        if result.get("skipped"):
            click.echo(f"Media {media_id} already has extraction, skipped")
        else:
            click.echo(f"Extracted text from media {media_id}")
            click.echo(f"  Confidence: {result.get('confidence', 0):.1f}%")
            click.echo(f"  Status: {result.get('status')}")

        if show_text:
            ext = Extraction.query.filter_by(media_id=media_id).first()
            if ext and ext.text:
                click.echo(f"\n--- Extracted Text ---\n{ext.text}\n")
    else:
        click.echo(f"Error: {result.get('error')}")


@ocr_cli.command()
@with_appcontext
def status() -> None:
    """Show OCR processing statistics."""
    from enferno.admin.models import Extraction, Media
    from sqlalchemy import func

    total_media = db.session.query(func.count(Media.id)).scalar() or 0

    stats = (
        db.session.query(
            Extraction.status, func.count(Extraction.id), func.avg(Extraction.confidence)
        )
        .group_by(Extraction.status)
        .all()
    )

    status_map = {row[0]: {"count": row[1], "avg_conf": row[2]} for row in stats}
    total_extracted = sum(s["count"] for s in status_map.values())
    pending = total_media - total_extracted

    click.echo(f"\nOCR Status Summary")
    click.echo(f"{'─' * 40}")
    click.echo(f"Total media:          {total_media:,}")
    click.echo(f"Pending (no OCR):     {pending:,}")
    click.echo(f"{'─' * 40}")

    for status_name in ["processed", "needs_review", "needs_transcription", "failed"]:
        data = status_map.get(status_name, {"count": 0, "avg_conf": None})
        count = data["count"]
        avg = data["avg_conf"]
        conf_str = f" (avg {avg:.1f}%)" if avg else ""
        click.echo(f"{status_name:21} {count:,}{conf_str}")

    click.echo(f"{'─' * 40}")
    click.echo(f"Total extracted:      {total_extracted:,}\n")
