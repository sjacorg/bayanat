# -*- coding: utf-8 -*-
"""Click commands."""
import os
import subprocess
import sys
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable

import click
import tomli
from flask import current_app
from flask.cli import AppGroup, with_appcontext
from flask_security.utils import hash_password
from sqlalchemy import event, MetaData, text

from enferno.admin.models import MigrationHistory, SystemInfo
from enferno.extensions import db, rds
from enferno.settings import Config
from enferno.tasks import restart_service as restart, perform_version_check
from enferno.tasks.update import perform_system_update_task
from enferno.user.models import User, Role
from enferno.utils.config_utils import ConfigManager
from enferno.utils.data_helpers import (
    create_default_location_data,
    generate_user_roles,
    generate_workflow_statues,
    import_default_data,
)
from enferno.utils.db_alignment_helpers import DBAlignmentChecker
from enferno.utils.logging_utils import get_logger
from enferno.utils.update_utils import rollback_update
from enferno.utils.validation_utils import validate_password_policy

logger = get_logger()


def say(message: str, level: str = "info") -> None:
    """Say a message (log and echo)."""
    getattr(logger, level)(message)
    click.echo(message)


# Function to log table creation
def log_table_creation(target, connection, tables=None, **kw):
    if tables is not None:
        for table in tables:
            logger.info(f"Creating table: {table.name}")


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
            say("Trigram extension installed successfully")
            conn.execute(text("CREATE EXTENSION if not exists postgis ;"))
            say("Postgis extension installed successfully")
            conn.commit()

    db.create_all()
    say("Database structure created successfully")
    generate_user_roles()
    say("Generated user roles successfully.")
    generate_workflow_statues()
    say("Generated system workflow statues successfully.")
    create_default_location_data()
    say("Generated location metadata successfully.")

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
        say("Imported data successfully.")
    except:
        say("Error importing data.", "error")


def run_migrations(dry_run: bool = False) -> list[str]:
    """Apply pending SQL migrations atomically."""
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text

    migrations_dir = Path(__file__).parent / "migrations"
    Session = sessionmaker(bind=db.engine)

    # Check pending migrations
    with Session() as session:
        migration_files = sorted(migrations_dir.glob("*.sql"))
        pending = [
            f.name for f in migration_files if not MigrationHistory.is_applied(f.name, session)
        ]

        if not pending:
            click.echo("✓ Database is up to date.")
            return []

        if dry_run:
            click.echo(f"Found {len(pending)} pending migrations:")
            click.echo("\n".join(f"  - {name}" for name in pending))
            return pending

    # Apply migrations with fresh session
    with Session() as session:
        with session.begin():
            applied = []

            for i, migration_name in enumerate(pending, 1):
                migration_file = migrations_dir / migration_name
                migration_sql = migration_file.read_text(encoding="utf-8").strip()

                if not migration_sql:
                    continue

                click.echo(f"[{i}/{len(pending)}] Applying {migration_name}...")

                session.execute(text(migration_sql))
                MigrationHistory.record_migration(migration_name, session)
                applied.append(migration_name)

        click.echo(f"✓ Applied {len(applied)} migrations successfully.")
        return applied


@click.command()
@click.option("--dry-run", is_flag=True, help="Check for pending migrations without applying them")
@with_appcontext
def apply_migrations(dry_run: bool = False) -> None:
    """Apply pending SQL migrations."""
    try:
        run_migrations(dry_run=dry_run)
    except Exception as e:
        click.echo(f"Error: {e}")
        sys.exit(1)


@click.command()
@with_appcontext
def get_version() -> None:
    """
    Get the current application version from both settings and database.
    """
    click.echo(f"Desired version (pyproject.toml): {Config.VERSION}")

    # Get deployed version from database
    deployed_version = SystemInfo.get_value("app_version")
    last_update = SystemInfo.get_value("last_update_time")

    if deployed_version:
        click.echo(f"Deployed version (database): {deployed_version}")
        if last_update:
            click.echo(f"Last update: {last_update}")

        if deployed_version == Config.VERSION:
            click.echo("System is up to date")
        else:
            click.echo("System is not up to date - run 'flask update-system' to update")
    else:
        click.echo("Deployed version: Not recorded (fresh installation?)")


@click.command()
@with_appcontext
def install() -> None:
    """Install a default Admin user and add an Admin role to it."""
    logger.info("Installing admin user.")
    admin_role = Role.query.filter(Role.name == "Admin").first()

    # check if there's an existing admin
    if admin_role.users.all():
        say("An admin user is already installed.", "error")
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
        say("Admin user installed successfully.")
    else:
        say("Error installing admin user.", "error")


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
        say("User already exists!", "error")
        return
    try:
        password = validate_password_policy(password)
    except ValueError as e:
        click.echo(str(e))
        return
    user = User(username=username, password=hash_password(password), active=1)
    if user.save():
        say("User created successfully")
    else:
        say("Error creating user.", "error")


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
        say("Sorry, this user does not exist!", "error")
    else:
        r = Role.query.filter(Role.name == role).first()
        if not role:
            click.echo("Sorry, this role does not exist!")
            u = click.prompt("Would you like to create one? Y/N", default="N")
            if u.lower() == "y":
                r = Role(name=role).save()
        # add role to user
        user.roles.append(r)
        say("Role {} added successfully to user {}".format(username, role))


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
        say("Specified user does not exist!", "error")
    else:
        try:
            password = validate_password_policy(password)
        except ValueError as e:
            click.echo(str(e))
            return
        user.password = hash_password(password)
        user.save()
        say("User password has been reset successfully.")
        if not user.active:
            say("Warning: User is not active!", "warning")


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
    try:
        subprocess.run(
            ["pybabel", "extract", "-F", "babel.cfg", "-k", "_l", "-o", "messages.pot", "."],
            check=True,
        )
    except subprocess.CalledProcessError:
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
    try:
        subprocess.run(
            ["pybabel", "update", "-i", "messages.pot", "-d", "enferno/translations"], check=True
        )
    except subprocess.CalledProcessError:
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
    try:
        subprocess.run(["pybabel", "compile", "-d", "enferno/translations"], check=True)
    except subprocess.CalledProcessError:
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


def verify_backup(backup_file: str) -> None:
    """Verify backup file integrity using pg_restore --list."""
    backup_path = Path(backup_file)

    # Check file exists and is not empty
    if not backup_path.exists():
        raise RuntimeError(f"Backup file not found: {backup_file}")

    file_size = backup_path.stat().st_size
    if file_size == 0:
        raise RuntimeError("Backup file is empty")

    logger.info(f"Verifying backup: {backup_file} ({file_size / 1024 / 1024:.1f}MB)")

    # Verify backup structure using pg_restore --list (fast, reads TOC only)
    try:
        result = subprocess.run(
            ["pg_restore", "--list", backup_file],
            capture_output=True,
            timeout=5,  # TOC read is very fast, 5s is generous
            check=True,
        )
        # If pg_restore can read the TOC, the backup structure is valid
        if not result.stdout:
            raise RuntimeError("Backup file appears corrupted")

        logger.info("Backup verification successful")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Backup verification timed out (file may be corrupted)")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Backup file is not a valid PostgreSQL dump: {e.stderr.decode()}")
    except FileNotFoundError:
        # pg_restore not in PATH - fall back to basic checks only
        logger.warning("pg_restore not found, skipping detailed backup verification")
        pass


def create_backup(output: Optional[str] = None, timeout: int = 300) -> Optional[str]:
    """Internal function to create a PostgreSQL database backup."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(current_app.root_path).parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    backup_file = output or str(backup_dir / f"{timestamp}_bayanat_backup.dump")

    db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not db_uri:
        click.echo("Error: No database URI configured")
        return None

    cmd = ["pg_dump", "-Fc", "-f", backup_file, f"--dbname={db_uri}"]

    try:
        logger.info("Starting database backup operation")
        subprocess.run(cmd, check=True, timeout=timeout)
        click.echo(f"Backup created: {backup_file}")

        # Verify backup integrity
        verify_backup(backup_file)

        return backup_file
    except Exception as e:
        click.echo(f"Backup failed: {e}")
        return None


@click.command()
@click.option("--output", "-o", help="Custom output file path for the backup", default=None)
@click.option(
    "--timeout", "-t", help="Timeout in seconds for the backup operation", default=300, type=int
)
@with_appcontext
def backup_db(output: Optional[str] = None, timeout: int = 300) -> Optional[str]:
    """Create a PostgreSQL database backup (CLI command)."""
    backup_file = create_backup(output, timeout)
    if not backup_file:
        raise click.ClickException("Backup creation failed")
    return backup_file


def restore_backup(backup_file: str, timeout: int = 3600) -> bool:
    """
    Internal function to restore PostgreSQL database from a backup file.

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

    # Build the pg_restore command for custom format
    cmd = ["pg_restore", "--clean", "--if-exists", f"--dbname={db_uri}", backup_file]

    # Execute the command
    try:
        logger.info("Starting database restore operation")
        click.echo("Restoring database... This may take a while.")

        # Run the command with timeout
        subprocess.run(cmd, check=True, timeout=timeout)

        # If we reach here, the command succeeded
        logger.info("Database restored successfully.")
        click.echo("Database restored successfully.")
        return True
    except Exception as e:
        logger.error(f"Database restoration failed: {str(e)}")
        click.echo(f"Database restoration failed: {str(e)}")
        return False


@click.command()
@click.argument("backup_file", type=click.Path(exists=True))
@click.option(
    "--timeout", "-t", help="Timeout in seconds for the restore operation", default=3600, type=int
)
@with_appcontext
def restore_db(backup_file: str, timeout: int = 3600) -> bool:
    """Restore PostgreSQL database from a backup file (CLI command)."""
    success = restore_backup(backup_file, timeout)
    if not success:
        raise click.ClickException("Database restoration failed")
    return success


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
        say("Maintenance mode enabled. System is locked.")
    else:
        say("Failed to enable maintenance mode.", "error")


@click.command(name="unlock")
@with_appcontext
def disable_maintenance():
    """
    Disable maintenance mode (unlock the application).
    """
    from enferno.utils.maintenance import disable_maintenance as dm

    if dm():
        say("Maintenance mode disabled. System is unlocked.")
    else:
        say("Failed to disable maintenance mode.", "error")


def run_system_update(skip_backup: bool = False, restart_service: bool = True) -> tuple[bool, str]:
    """
    Update system: git pull, dependencies, migrations, and restart services.
    Automatically rolls back on failure.

    Returns:
        tuple[bool, str]: (success, message)
    """
    logger.info("Starting system update")

    project_root = Path(current_app.root_path).parent
    stashed = False
    backup_file = None
    git_commit_before = None

    try:
        # Record current git commit for rollback
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=project_root,
        )
        git_commit_before = result.stdout.strip()
        logger.info(f"Current commit: {git_commit_before[:8]}")

        # 1) Backup database
        if not skip_backup:
            click.echo("Creating database backup...")
            backup_file = create_backup(timeout=300)
            if not backup_file:
                raise RuntimeError("Database backup failed")
            logger.info(f"Backup created: {backup_file}")

        # 2) Git: stash local changes if any, then pull
        status = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, cwd=project_root
        )
        if status.stdout.strip():
            click.echo("Stashing local changes...")
            subprocess.run(
                ["git", "stash", "push", "-m", "auto-update stash"], check=True, cwd=project_root
            )
            stashed = True

        click.echo("Pulling code updates...")
        subprocess.run(["git", "pull", "--ff-only"], check=True, timeout=120, cwd=project_root)
        new_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=project_root
        ).stdout.strip()
        logger.info(f"Pulled to commit: {new_commit[:8]}")

        # 3) Dependencies
        click.echo("Installing dependencies...")
        subprocess.run(["uv", "sync", "--frozen"], check=True, timeout=600, cwd=project_root)
        logger.info("Dependencies installed")

        # 4) Migrations
        run_migrations()
        logger.info("Migrations completed")

        # 5) Update version in database
        pyproject_path = project_root / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomli.load(f)
            new_version = pyproject_data["project"]["version"]

        # Update version and timestamp in one go
        version_entry = SystemInfo.query.filter_by(key="app_version").first()
        if version_entry:
            version_entry.value = new_version
        else:
            db.session.add(SystemInfo(key="app_version", value=new_version))

        update_time_entry = SystemInfo.query.filter_by(key="last_update_time").first()
        if update_time_entry:
            update_time_entry.value = datetime.now().isoformat()
        else:
            db.session.add(SystemInfo(key="last_update_time", value=datetime.now().isoformat()))

        db.session.commit()
        logger.info(f"Version updated to {new_version}")

        # Update cache to reflect new version (maintains accuracy)
        # Use current timestamp so UI knows update just completed
        checked_at = datetime.now(timezone.utc).isoformat()
        rds.set("bayanat:update:latest", f"{new_version}|{checked_at}")
        logger.info(f"Updated version cache to {new_version}")

        # 6) Restart services
        if restart_service:
            click.echo("Restarting services...")
            restart("bayanat")
            restart("bayanat-celery")
            logger.info("Services restarted")

        logger.info("System update completed successfully")
        return (True, "System updated successfully")

    except Exception as e:
        # ROLLBACK on any failure
        logger.error(f"Update failed, rolling back: {e}")
        click.echo(f"Update failed: {e}")

        rollback_update(
            git_commit=git_commit_before,
            backup_file=backup_file,
            restart_service=restart_service,
        )

        return (False, f"Update failed and rolled back: {e}")
    finally:
        if stashed:
            try:
                click.echo("Restoring stashed changes...")
                subprocess.run(["git", "stash", "pop"], check=True, cwd=project_root)
            except subprocess.CalledProcessError as pop_err:
                logger.warning(f"Stash restore failed (likely due to build artifacts): {pop_err}")
                click.echo("Note: Stash preserved - run 'git stash list' to see saved changes.")


@click.command()
@click.option("--skip-backup", is_flag=True, help="Skip database backup")
@with_appcontext
def update_system(skip_backup: bool = False) -> None:
    """CLI command to perform system update. Blocks until completion."""
    result = perform_system_update_task(skip_backup=skip_backup)
    message = result.get("message") or result.get("error", "System update completed")
    click.echo(message)
    if not result.get("success"):
        raise click.ClickException(message)


@click.command()
@with_appcontext
def check_updates() -> None:
    """
    Check for new Bayanat versions from GitHub and cache result.
    Called by: periodic task (every 12h) and CLI for manual testing.
    """
    click.echo(f"Current version: {Config.VERSION}")
    click.echo("Checking for updates from GitHub...")

    result = perform_version_check()

    if result:
        if result["update_available"]:
            click.echo(f"✓ Update available: {result['latest_version']}")
            click.echo(f"  Checked at: {result['checked_at']}")
            click.echo(f"  Repository: {result['repository']}")
        else:
            click.echo(f"✓ System is up to date (latest: {result['latest_version']})")
    else:
        click.echo("✗ Update check failed (see logs for details)", err=True)
