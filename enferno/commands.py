# -*- coding: utf-8 -*-
"""Click commands."""
import os
import sys
from datetime import datetime
import subprocess
import click
from flask.cli import AppGroup
from flask.cli import with_appcontext
from flask_security.utils import hash_password
from flask import current_app
from pathlib import Path
from typing import Optional

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
from enferno.admin.models import MigrationHistory, SystemInfo
from sqlalchemy import event, MetaData, text
from sqlalchemy.engine.url import make_url

logger = get_logger()


# Function to log table creation
def log_table_creation(target, connection, tables=None, **kw):
    if tables is not None:
        for table in tables:
            logger.info(f"Creating table: {table.name}")


def _initialize_db_state() -> None:
    """
    Internal function to initialize database state on first setup.
    This handles both marking migrations as applied and setting initial version info.
    """
    # Step 1: Mark migrations as applied
    # The migrations directory is inside the enferno package
    migration_dir = os.path.join(os.path.dirname(__file__), "migrations")

    # Ensure the directory exists
    if not os.path.exists(migration_dir):
        click.echo(f"Error: Migration directory '{migration_dir}' not found.")
        return

    # Get all .sql files in the migrations directory, sorted by timestamp prefix
    migration_files = sorted([f for f in os.listdir(migration_dir) if f.endswith(".sql")])

    # Loop through each migration file and mark it as applied
    for migration_file in migration_files:
        if not MigrationHistory.is_applied(migration_file):
            # Record the migration in the database
            MigrationHistory.record_migration(migration_file)
            click.echo(f"Migration {migration_file} marked as applied.")

    # Step 2: Initialize version information
    try:
        # Set initial app version
        version_entry = SystemInfo(key="app_version", value=Config.VERSION)
        db.session.add(version_entry)

        # Add initial timestamp
        update_time = datetime.now().isoformat()
        update_time_entry = SystemInfo(key="last_update_time", value=update_time)
        db.session.add(update_time_entry)

        # Commit all changes in one transaction
        db.session.commit()

        click.echo("All valid SQL migrations have been marked as applied.")
        click.echo(f"System version set to {Config.VERSION}")
    except Exception as e:
        db.session.rollback()
        click.echo(f"Warning: Could not fully initialize database state: {str(e)}")
        # Try at least to commit the migrations
        db.session.commit()


@click.command()
@with_appcontext
def mark_migrations_applied() -> None:
    """
    Command wrapper to initialize database state.
    This marks all migrations as applied and sets up version tracking.
    Should be run when initializing the system for the first time.
    """
    _initialize_db_state()


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

    # Initialize database state (mark migrations and set version)
    _initialize_db_state()

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

    migration_files = sorted([f for f in os.listdir(migration_dir) if f.endswith(".sql")])
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
@click.argument("version", required=True)
@with_appcontext
def set_version(version: str) -> None:
    """
    Set the current application version in the database.

    Args:
        version: The version string to set
    """
    # Check if the version is the same as in settings
    if version != Config.VERSION:
        click.echo(
            f"Warning: The version you're setting ({version}) doesn't match the version in settings ({Config.VERSION})."
        )
        confirm = click.confirm("Do you want to proceed anyway?")
        if not confirm:
            click.echo("Operation cancelled.")
            return

    try:
        # Get existing entry or create new one
        version_entry = SystemInfo.query.filter_by(key="app_version").first()
        if version_entry:
            version_entry.value = version
        else:
            version_entry = SystemInfo(key="app_version", value=version)
            db.session.add(version_entry)

        # Add update timestamp
        update_time_entry = SystemInfo.query.filter_by(key="last_update_time").first()
        update_time = datetime.now().isoformat()
        if update_time_entry:
            update_time_entry.value = update_time
        else:
            update_time_entry = SystemInfo(key="last_update_time", value=update_time)
            db.session.add(update_time_entry)

        db.session.commit()
        click.echo(f"Successfully set application version to {version}")
    except Exception as e:
        click.echo(f"Error setting version: {str(e)}")
        sys.exit(1)


@click.command()
@with_appcontext
def get_version() -> None:
    """
    Get the current application version from both settings and database.
    """
    settings_version = Config.VERSION
    version_entry = SystemInfo.query.filter_by(key="app_version").first()
    db_version = version_entry.value if version_entry else "Not set"

    click.echo(f"Settings version: {settings_version}")
    click.echo(f"Database version: {db_version}")

    # Show last update time if available
    update_time_entry = SystemInfo.query.filter_by(key="last_update_time").first()
    if update_time_entry:
        click.echo(f"Last updated: {update_time_entry.value}")

    if settings_version != db_version and db_version != "Not set":
        click.echo("\nWarning: The version in settings doesn't match the version in the database.")
        click.echo("This could indicate incomplete migrations or an inconsistent state.")


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


def parse_pg_uri(db_uri: str) -> dict:
    """
    Parse a PostgreSQL connection URI into its components using SQLAlchemy.

    Args:
        db_uri: The PostgreSQL connection URI

    Returns:
        Dictionary with connection parameters
    """

    # Initialize with empty values
    result = {"username": None, "password": None, "host": None, "port": None, "dbname": None}

    # Handle empty URI
    if not db_uri:
        logger.warning("Empty database URI provided")
        return result

    try:
        url = make_url(db_uri)
        result["username"] = url.username
        result["password"] = url.password
        result["host"] = url.host
        result["port"] = url.port
        result["dbname"] = url.database
    except Exception as e:
        logger.error(f"Error parsing database URI: {e}")

    return result


@click.command()
@click.option("--output", "-o", help="Custom output file path for the backup", default=None)
@click.option(
    "--timeout", "-t", help="Timeout in seconds for the backup operation", default=300, type=int
)
@with_appcontext
def backup_db(output: Optional[str] = None, timeout: int = 300) -> Optional[str]:
    """
    Create a backup of the PostgreSQL database.

    Args:
        output: Optional custom output path for the backup file
        timeout: Timeout in seconds for the backup operation (default: 300)

    Returns:
        Path to the created backup file or None if backup failed
    """
    logger.info("Creating database backup.")

    # Get timestamp for the backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create backup directory if it doesn't exist
    backup_dir = Path(current_app.root_path) / ".." / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Get database URI from app config
    db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not db_uri:
        logger.error("Database URI not found in application config.")
        click.echo("Error: Database URI not found in application config.")
        return None

    # Parse the database URI
    db_info = parse_pg_uri(db_uri)

    # Use provided output path or create one in backups directory
    if output:
        backup_file = output
    else:
        # Put timestamp at the beginning for better sorting
        backup_file = str(backup_dir / f"{timestamp}_bayanat_backup.dump")

    # Build the pg_dump command with custom format (compressed)
    cmd = ["pg_dump", "-Fc", "-f", backup_file]

    # Add connection parameters only if they exist
    if db_info["username"]:
        cmd.extend(["-U", db_info["username"]])

    if db_info["host"]:
        cmd.extend(["-h", db_info["host"]])

    if db_info["port"]:
        cmd.extend(["-p", str(db_info["port"])])

    # Add database name
    if db_info["dbname"]:
        cmd.append(db_info["dbname"])

    # Execute the command
    try:
        # Set PGPASSWORD environment variable if password exists
        env = os.environ.copy()
        if db_info["password"]:
            env["PGPASSWORD"] = db_info["password"]

        logger.info(f"Running database backup command: {' '.join(cmd)}")
        click.echo(f"Creating database backup at: {backup_file}")

        # Run the command with timeout
        process = subprocess.run(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=timeout,
        )

        logger.info(f"Database backup created successfully at {backup_file}")
        click.echo(f"Database backup created successfully at {backup_file}")
        return backup_file

    except subprocess.TimeoutExpired:
        logger.error(f"Database backup timed out after {timeout} seconds")
        click.echo(f"Database backup timed out after {timeout} seconds")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"Database backup failed: {e.stderr}")
        click.echo(f"Database backup failed: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"Error creating database backup: {str(e)}")
        click.echo(f"Error creating database backup: {str(e)}")
        return None


@click.command()
@click.argument("backup_file", type=click.Path(exists=True))
@click.option(
    "--timeout", "-t", help="Timeout in seconds for the restore operation", default=3600, type=int
)
@with_appcontext
def restore_db(backup_file: str, timeout: int = 3600) -> bool:
    """
    Restore PostgreSQL database from a backup file.

    Args:
        backup_file: Path to the backup file
        timeout: Timeout in seconds for the restore operation (default: 3600)

    Returns:
        True if restoration was successful, False otherwise
    """
    logger.info(f"Restoring database from backup: {backup_file}")
    click.echo(f"Restoring database from backup: {backup_file}")

    # Get database URI from app config
    db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not db_uri:
        logger.error("Database URI not found in application config.")
        click.echo("Error: Database URI not found in application config.")
        return False

    # Parse the database URI
    db_info = parse_pg_uri(db_uri)

    # Build the pg_restore command for custom format
    cmd = ["pg_restore", "--clean", "--if-exists"]

    # Add database name if present
    if db_info["dbname"]:
        cmd.extend(["-d", db_info["dbname"]])

    # Add connection parameters only if they exist
    if db_info["username"]:
        cmd.extend(["-U", db_info["username"]])

    if db_info["host"]:
        cmd.extend(["-h", db_info["host"]])

    if db_info["port"]:
        cmd.extend(["-p", db_info["port"]])

    # Add the backup file
    cmd.append(backup_file)

    # Execute the command
    try:
        # Set PGPASSWORD environment variable if password exists
        env = os.environ.copy()
        if db_info["password"]:
            env["PGPASSWORD"] = db_info["password"]

        logger.info(f"Running database restore command: {' '.join(cmd)}")
        click.echo("Restoring database... This may take a while.")

        # Run the command with timeout
        process = subprocess.run(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=timeout,
        )

        if process.returncode == 0:
            logger.info("Database restored successfully.")
            click.echo("Database restored successfully.")
            return True
        else:
            logger.error(f"Database restoration failed: {process.stderr}")
            click.echo(f"Database restoration failed: {process.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"Database restoration timed out after {timeout} seconds")
        click.echo(f"Database restoration timed out after {timeout} seconds")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Database restoration failed: {e.stderr}")
        click.echo(f"Database restoration failed: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error restoring database: {str(e)}")
        click.echo(f"Error restoring database: {str(e)}")
        return False


@click.command(name="lock")
@click.option("--reason", "-r", help="Reason for maintenance", default="System maintenance")
@with_appcontext
def enable_maintenance(reason):
    """
    Enable maintenance mode (lock the application).

    Args:
        reason: Reason for enabling maintenance mode
    """
    from enferno.utils.maintenance import enable_maintenance as em

    if em(reason):
        click.echo("Maintenance mode enabled. System is locked.")
        logger.info("Maintenance mode enabled via CLI.")
    else:
        click.echo("Failed to enable maintenance mode.")
        logger.error("Failed to enable maintenance mode via CLI.")


@click.command(name="unlock")
@with_appcontext
def disable_maintenance():
    """
    Disable maintenance mode (unlock the application).
    """
    from enferno.utils.maintenance import disable_maintenance as dm

    if dm():
        click.echo("Maintenance mode disabled. System is unlocked.")
        logger.info("Maintenance mode disabled via CLI.")
    else:
        click.echo("Failed to disable maintenance mode.")
        logger.error("Failed to disable maintenance mode via CLI.")
