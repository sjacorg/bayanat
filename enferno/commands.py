# -*- coding: utf-8 -*-
"""Click commands."""
import os
import sys
import click
from flask.cli import AppGroup
from flask.cli import with_appcontext
from flask_security.utils import hash_password

from enferno.settings import Config
from enferno.extensions import db
from enferno.user.models import User, Role
from enferno.utils.data_helpers import (
    import_default_data,
    generate_user_roles,
    generate_workflow_statues,
    create_default_location_data,
)
from enferno.utils.config_utils import ConfigManager
from enferno.utils.db_alignment_helpers import DBAlignmentChecker
from enferno.utils.logging_utils import get_logger
from enferno.admin.models import MigrationHistory
from sqlalchemy import event, MetaData, text
from natsort import natsorted

logger = get_logger()


# Function to log table creation
def log_table_creation(target, connection, tables=None, **kw):
    if tables is not None:
        for table in tables:
            logger.info(f"Creating table: {table.name}")


def _mark_migrations_applied() -> None:
    """
    Internal function to mark all valid SQL migrations as applied.
    This should be run when initializing the system for the first time
    so that all past migrations are marked as applied.
    """
    # The migrations directory is inside the enferno package
    migration_dir = os.path.join(os.path.dirname(__file__), "migrations")

    # Ensure the directory exists
    if not os.path.exists(migration_dir):
        click.echo(f"Error: Migration directory '{migration_dir}' not found.")
        return

    # Get all .sql files in the migrations directory, sorted by natural name
    migration_files = natsorted([f for f in os.listdir(migration_dir) if f.endswith(".sql")])

    # Loop through each migration file and mark it as applied
    for migration_file in migration_files:
        if not MigrationHistory.is_applied(migration_file):
            # Record the migration in the database
            MigrationHistory.record_migration(migration_file)
            click.echo(f"Migration {migration_file} marked as applied.")

    # Commit the session to ensure all migrations are recorded
    db.session.commit()

    click.echo("All valid SQL migrations have been marked as applied.")


@click.command()
@with_appcontext
def mark_migrations_applied() -> None:
    """
    Command wrapper to mark all valid SQL migrations as applied.
    This should be run when initializing the system for the first time
    so that all past migrations are marked as applied.
    """
    _mark_migrations_applied()


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

    # Attach the event listener for table creation
    metadata = db.metadata
    event.listen(metadata, "before_create", log_table_creation)

    # create db exts if required, needs superuser db permissions
    if create_exts:
        with db.engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION if not exists pg_trgm ;"))
            click.echo("Trigram extension installed successfully")
            logger.info("Trigram extension installed successfully")
            conn.execute(text("CREATE EXTENSION if not exists postgis ;"))
            logger.info("Postgis extension installed successfully")
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

    # Mark all migrations as applied on initial DB creation
    _mark_migrations_applied()

    # Remove the event listener after creation
    event.remove(metadata, "before_create", log_table_creation)


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
@click.option("--dry-run", is_flag=True, help="Check for pending migrations without applying them")
@with_appcontext
def apply_migrations(dry_run: bool = False) -> None:
    """
    Apply all pending SQL migrations in the correct order and mark them as applied.
    This should be run during application updates when new migrations are present.
    """
    migration_dir = os.path.join(os.path.dirname(__file__), "migrations")

    if not os.path.exists(migration_dir):
        click.echo(f"Error: Migration directory '{migration_dir}' not found.")
        sys.exit(1)

    migration_files = natsorted([f for f in os.listdir(migration_dir) if f.endswith(".sql")])
    pending_migrations = [f for f in migration_files if not MigrationHistory.is_applied(f)]

    if not pending_migrations:
        click.echo("No pending migrations to apply.")
        return

    if dry_run:
        click.echo("Pending migrations:")
        for migration in pending_migrations:
            click.echo(f"  - {migration}")
        return

    connection = db.session.connection()
    trans = connection.begin()

    try:
        click.echo("Starting migration process...")
        for migration_file in pending_migrations:
            migration_path = os.path.join(migration_dir, migration_file)
            with open(migration_path, "r") as sql_file:
                migration_sql = sql_file.read()

            problematic_commands = ["CREATE DATABASE", "DROP DATABASE", "VACUUM"]
            if any(cmd in migration_sql.upper() for cmd in problematic_commands):
                click.echo(
                    f"Warning: Migration {migration_file} contains commands that cannot be rolled back!"
                )
                click.echo("Consider splitting these operations into separate migrations.")

            connection.execute(text(migration_sql))
            click.echo(f"Applied migration: {migration_file}")
            MigrationHistory.record_migration(migration_file)

        trans.commit()
        click.echo("[Success] All pending migrations have been applied.")

    except Exception as e:
        trans.rollback()
        click.echo("[Failed] Rolling back all migrations due to error.")
        click.echo(f"Error details: {str(e)}")
        sys.exit(1)


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
