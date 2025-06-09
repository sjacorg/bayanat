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
@click.option("--cleanup", is_flag=True, help="Clean up test data after running")
@with_appcontext
def test_dynamic_fields(cleanup: bool) -> None:
    """Test dynamic fields functionality by creating test fields of each type."""
    logger.info("Starting dynamic fields test")

    # Clean up any existing test fields first
    logger.info("Cleaning up existing test fields")
    try:
        fields_to_cleanup = DynamicField.query.filter(DynamicField.name.like("test_%")).all()
        for field in fields_to_cleanup:
            field.drop_column()
            field.delete()
        db.session.commit()
    except Exception as e:
        logger.error(f"Error during initial cleanup: {str(e)}")
        db.session.rollback()
        return

    test_fields = [
        {
            "name": "test_string_field",
            "title": "Test String Field",
            "field_type": DynamicField.STRING,
            "ui_component": DynamicField.UIComponent.TEXT_INPUT,
            "config": {"max_length": 100},
            "test_value": "Hello World",
            "help_text": "A test string field",
            "sort_order": 1,
            "default_value": "Hello World",
            "readonly": False,
            "hidden": False,
        },
        {
            "name": "test_dropdown_field",
            "title": "Test Dropdown Field",
            "field_type": DynamicField.STRING,
            "ui_component": DynamicField.UIComponent.DROPDOWN,
            "options": ["Option 1", "Option 2", "Option 3"],
            "test_value": "Option 1",
            "help_text": "A test dropdown field",
            "sort_order": 2,
            "default_value": "Option 1",
            "readonly": False,
            "hidden": False,
        },
        {
            "name": "test_integer_field",
            "title": "Test Integer Field",
            "field_type": DynamicField.INTEGER,
            "ui_component": DynamicField.UIComponent.NUMBER,
            "config": {"min": 0, "max": 100},
            "test_value": 42,
            "help_text": "A test integer field",
            "sort_order": 3,
            "default_value": 42,
            "readonly": False,
            "hidden": False,
        },
        {
            "name": "test_datetime_field",
            "title": "Test DateTime Field",
            "field_type": DynamicField.DATETIME,
            "ui_component": DynamicField.UIComponent.DATE_PICKER,
            "config": {"format": "YYYY-MM-DD"},
            "test_value": datetime.now(timezone.utc),
            "help_text": "A test datetime field",
            "sort_order": 4,
            "default_value": datetime.now(timezone.utc),
            "readonly": False,
            "hidden": False,
        },
        {
            "name": "test_array_field",
            "title": "Test Array Field",
            "field_type": DynamicField.ARRAY,
            "ui_component": DynamicField.UIComponent.MULTI_SELECT,
            "options": ["Tag 1", "Tag 2", "Tag 3"],
            "test_value": ["Tag 1", "Tag 2"],
            "help_text": "A test array field",
            "sort_order": 5,
            "default_value": ["Tag 1", "Tag 2"],
            "readonly": False,
            "hidden": False,
        },
        {
            "name": "test_text_field",
            "title": "Test Text Field",
            "field_type": DynamicField.TEXT,
            "ui_component": DynamicField.UIComponent.TEXT_AREA,
            "test_value": "This is a longer text field\nwith multiple lines",
            "help_text": "A test text field",
            "sort_order": 6,
            "default_value": "This is a longer text field\nwith multiple lines",
            "readonly": False,
            "hidden": False,
        },
        {
            "name": "test_boolean_field",
            "title": "Test Boolean Field",
            "field_type": DynamicField.BOOLEAN,
            "ui_component": DynamicField.UIComponent.CHECKBOX,
            "test_value": True,
            "help_text": "A test boolean field",
            "sort_order": 7,
            "default_value": True,
            "readonly": False,
            "hidden": False,
        },
        {
            "name": "test_float_field",
            "title": "Test Float Field",
            "field_type": DynamicField.FLOAT,
            "ui_component": DynamicField.UIComponent.NUMBER,
            "config": {"precision": 8, "scale": 2},
            "test_value": 3.14159,
            "help_text": "A test float field",
            "sort_order": 8,
            "default_value": 3.14159,
            "readonly": False,
            "hidden": False,
        },
        {
            "name": "test_json_field",
            "title": "Test JSON Field",
            "field_type": DynamicField.JSON,
            "ui_component": DynamicField.UIComponent.TEXT_AREA,
            "test_value": {"key": "value", "nested": {"data": "test"}},
            "help_text": "A test json field",
            "sort_order": 9,
            "default_value": {"key": "value", "nested": {"data": "test"}},
            "readonly": False,
            "hidden": False,
        },
    ]

    created_fields = []
    try:
        # Create fields
        for field_data in test_fields:
            try:
                logger.info(f"Creating {field_data['name']}")
                field = DynamicField(
                    name=field_data["name"],
                    title=field_data["title"],
                    entity_type="bulletin",
                    field_type=field_data["field_type"],
                    ui_component=field_data["ui_component"],
                    config=field_data.get("config", {}),
                    options=field_data.get("options", []),
                    help_text=field_data["help_text"],
                    sort_order=field_data["sort_order"],
                    default_value=field_data["default_value"],
                    readonly=field_data["readonly"],
                    hidden=field_data["hidden"],
                )
                field.save()
                field.create_column()
                created_fields.append(field)
                db.session.commit()
                click.echo(f"Created {field_data['name']} successfully")
            except Exception as e:
                logger.error(f"Error creating field {field_data['name']}: {str(e)}")
                db.session.rollback()
                if cleanup:
                    cleanup_test_data()
                return

        # Create and test bulletin
        try:
            logger.info("Creating test bulletin")
            bulletin = Bulletin(title="Test Bulletin", description="Testing dynamic fields")
            bulletin.save()

            # Test setting values
            for field_data in test_fields:
                setattr(bulletin, field_data["name"], field_data["test_value"])

            bulletin.save()
            db.session.commit()
            click.echo("\nTest bulletin created successfully!")

            # Verify values
            click.echo("\nField values:")
            for field_data in test_fields:
                value = getattr(bulletin, field_data["name"])
                click.echo(
                    f"{field_data['title']}: {value} (help_text: {field_data['help_text']}, default: {field_data['default_value']}, readonly: {field_data['readonly']}, hidden: {field_data['hidden']})"
                )

        except Exception as e:
            logger.error(f"Error testing bulletin: {str(e)}")
            db.session.rollback()
            if cleanup:
                cleanup_test_data()
            return

        # Refresh schema at the end
        db.Model.metadata.clear()
        db.session.remove()
        db.create_all()

        if cleanup:
            cleanup_test_data()
            click.echo("\nCleanup complete!")
        else:
            click.echo("\nTest data remains in database. Use --cleanup flag to remove test data.")

    except Exception as e:
        logger.error(f"Error in test_dynamic_fields: {str(e)}")
        db.session.rollback()
        if cleanup:
            cleanup_test_data()


def cleanup_test_data():
    """Clean up test dynamic fields and bulletin."""
    logger.info("Cleaning up test data")

    try:
        # Delete test bulletin first
        test_bulletin = Bulletin.query.filter_by(title="Test Bulletin").first()
        if test_bulletin:
            test_bulletin.delete()
            db.session.commit()

        # Drop columns and delete dynamic fields
        fields = DynamicField.query.filter(DynamicField.name.like("test_%")).all()
        for field in fields:
            try:
                field.drop_column()
                field.delete()
                db.session.commit()
            except Exception as e:
                logger.error(f"Error cleaning up field {field.name}: {str(e)}")
                db.session.rollback()

        # Refresh SQLAlchemy models at the end
        db.Model.metadata.clear()
        db.session.remove()
        db.create_all()

    except Exception as e:
        logger.error(f"Error in cleanup: {str(e)}")
        db.session.rollback()


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
