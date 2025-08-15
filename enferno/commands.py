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
from enferno.utils.date_helper import DateHelper

from enferno.utils.validation_utils import validate_password_policy

logger = get_logger()


def generate_core_fields():
    """Generate core fields as DynamicField records in the database."""
    from enferno.admin.models.core_fields import BULLETIN_CORE_FIELDS

    # Check if core fields already exist
    existing_core_fields = DynamicField.query.filter_by(core=True, entity_type="bulletin").count()
    if existing_core_fields > 0:
        logger.info("Core fields already exist, skipping generation")
        return

    logger.info("Generating core fields as DynamicField records")

    for field_name, field_config in BULLETIN_CORE_FIELDS.items():
        try:
            core_field = DynamicField(
                name=field_name,
                title=field_config["title"],
                entity_type="bulletin",
                field_type=field_config["field_type"],
                ui_component=field_config["ui_component"],
                schema_config={},
                ui_config={},
                validation_config={},
                options=field_config.get("options", []),
                active=field_config["visible"],
                searchable=False,
                sort_order=field_config["sort_order"],
                core=True,  # Mark as core field
            )
            core_field.save()
            logger.info(f"Created core field: {field_name}")

        except Exception as e:
            logger.error(f"Error creating core field {field_name}: {str(e)}")
            continue

    db.session.commit()
    logger.info("Core fields generation completed")


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
            "schema_config": {"required": True, "default": "Hello World"},
            "ui_config": {
                "label": "Test String Field",
                "help_text": "A test string field",
                "sort_order": 1,
                "readonly": False,
                "hidden": False,
                "group": "main",
                "width": "full",
            },
            "validation_config": {"max_length": 100},
            "options": [],
            "test_value": "Hello World",
        },
        {
            "name": "test_dropdown_field",
            "title": "Test Dropdown Field",
            "field_type": DynamicField.STRING,
            "ui_component": DynamicField.UIComponent.DROPDOWN,
            "schema_config": {"required": False, "default": "Option 1"},
            "ui_config": {
                "label": "Test Dropdown Field",
                "help_text": "A test dropdown field",
                "sort_order": 2,
                "readonly": False,
                "hidden": False,
                "group": "main",
                "width": "half",
            },
            "validation_config": {},
            "options": [
                {"label": "Option 1", "value": "option1"},
                {"label": "Option 2", "value": "option2"},
                {"label": "Option 3", "value": "option3"},
            ],
            "test_value": "Option 1",
        },
        {
            "name": "test_integer_field",
            "title": "Test Integer Field",
            "field_type": DynamicField.INTEGER,
            "ui_component": DynamicField.UIComponent.NUMBER,
            "schema_config": {"required": False, "default": 42},
            "ui_config": {
                "label": "Test Integer Field",
                "help_text": "A test integer field",
                "sort_order": 3,
                "readonly": False,
                "hidden": False,
                "group": "details",
                "width": "half",
            },
            "validation_config": {"min": 0, "max": 100},
            "options": [],
            "test_value": 42,
        },
        {
            "name": "test_datetime_field",
            "title": "Test DateTime Field",
            "field_type": DynamicField.DATETIME,
            "ui_component": DynamicField.UIComponent.DATE_PICKER,
            "schema_config": {
                "required": False,
                "default": DateHelper.serialize_datetime(datetime.now(timezone.utc)),
            },
            "ui_config": {
                "label": "Test DateTime Field",
                "help_text": "A test datetime field",
                "sort_order": 4,
                "readonly": False,
                "hidden": False,
                "group": "details",
                "width": "full",
            },
            "validation_config": {"format": "YYYY-MM-DD"},
            "options": [],
            "test_value": DateHelper.serialize_datetime(datetime.now(timezone.utc)),
        },
        {
            "name": "test_array_field",
            "title": "Test Array Field",
            "field_type": DynamicField.ARRAY,
            "ui_component": DynamicField.UIComponent.MULTI_SELECT,
            "schema_config": {"required": False, "default": ["Tag 1", "Tag 2"]},
            "ui_config": {
                "label": "Test Array Field",
                "help_text": "A test array field",
                "sort_order": 5,
                "readonly": False,
                "hidden": False,
            },
            "validation_config": {},
            "options": [
                {"label": "Tag 1", "value": "tag1"},
                {"label": "Tag 2", "value": "tag2"},
                {"label": "Tag 3", "value": "tag3"},
            ],
            "test_value": ["Tag 1", "Tag 2"],
        },
        {
            "name": "test_text_field",
            "title": "Test Text Field",
            "field_type": DynamicField.TEXT,
            "ui_component": DynamicField.UIComponent.TEXT_AREA,
            "schema_config": {
                "required": False,
                "default": "This is a longer text field\nwith multiple lines",
            },
            "ui_config": {
                "label": "Test Text Field",
                "help_text": "A test text field",
                "sort_order": 6,
                "readonly": False,
                "hidden": False,
            },
            "validation_config": {},
            "options": [],
            "test_value": "This is a longer text field\nwith multiple lines",
        },
        {
            "name": "test_boolean_field",
            "title": "Test Boolean Field",
            "field_type": DynamicField.BOOLEAN,
            "ui_component": DynamicField.UIComponent.CHECKBOX,
            "schema_config": {"required": False, "default": True},
            "ui_config": {
                "label": "Test Boolean Field",
                "help_text": "A test boolean field",
                "sort_order": 7,
                "readonly": False,
                "hidden": False,
            },
            "validation_config": {},
            "options": [],
            "test_value": True,
        },
        {
            "name": "test_float_field",
            "title": "Test Float Field",
            "field_type": DynamicField.FLOAT,
            "ui_component": DynamicField.UIComponent.NUMBER,
            "schema_config": {"required": False, "default": 3.14159},
            "ui_config": {
                "label": "Test Float Field",
                "help_text": "A test float field",
                "sort_order": 8,
                "readonly": False,
                "hidden": False,
            },
            "validation_config": {"precision": 8, "scale": 2},
            "options": [],
            "test_value": 3.14159,
        },
        {
            "name": "test_json_field",
            "title": "Test JSON Field",
            "field_type": DynamicField.JSON,
            "ui_component": DynamicField.UIComponent.TEXT_AREA,
            "schema_config": {
                "required": False,
                "default": {"key": "value", "nested": {"data": "test"}},
            },
            "ui_config": {
                "label": "Test JSON Field",
                "help_text": "A test json field",
                "sort_order": 9,
                "readonly": False,
                "hidden": False,
            },
            "validation_config": {},
            "options": [],
            "test_value": {"key": "value", "nested": {"data": "test"}},
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
                    schema_config=field_data.get("schema_config", {}),
                    ui_config=field_data.get("ui_config", {}),
                    validation_config=field_data.get("validation_config", {}),
                    options=field_data.get("options", []),
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
                ui = field_data.get("ui_config", {})
                schema = field_data.get("schema_config", {})
                click.echo(
                    f"{field_data['title']}: {value} (group: {ui.get('group')}, width: {ui.get('width')}, help_text: {ui.get('help_text')}, default: {schema.get('default')}, readonly: {ui.get('readonly')}, hidden: {ui.get('hidden')})"
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
