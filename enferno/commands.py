# -*- coding: utf-8 -*-
"""Click commands."""
import os
import subprocess
import sys
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

import click
import tomli
from flask import current_app
from flask.cli import AppGroup, with_appcontext
from flask_security.utils import hash_password
from sqlalchemy import event, MetaData, text
from sqlalchemy.engine.url import make_url

from enferno.admin.models import MigrationHistory, SystemInfo
from enferno.extensions import db
from enferno.settings import Config
from enferno.tasks import restart_service as restart
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
from enferno.utils.validation_utils import validate_password_policy

logger = get_logger()


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


def parse_pg_uri(db_uri: str) -> dict:
    """Parse PostgreSQL URI into connection parameters."""
    if not db_uri:
        return {"username": None, "password": None, "host": None, "port": None, "dbname": None}

    try:
        url = make_url(db_uri)
        return {
            "username": url.username,
            "password": url.password,
            "host": url.host,
            "port": url.port,
            "dbname": url.database,
        }
    except Exception as e:
        logger.error(f"Error parsing database URI: {e}")
        return {"username": None, "password": None, "host": None, "port": None, "dbname": None}


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

    db_info = parse_pg_uri(db_uri)
    cmd = ["pg_dump", "-Fc", "-f", backup_file]

    if db_info["username"]:
        cmd.extend(["-U", db_info["username"]])
    if db_info["host"]:
        cmd.extend(["-h", db_info["host"]])
    if db_info["port"]:
        cmd.extend(["-p", str(db_info["port"])])
    if db_info["dbname"]:
        cmd.append(db_info["dbname"])

    try:
        env = os.environ.copy()
        if db_info["password"]:
            env["PGPASSWORD"] = db_info["password"]

        subprocess.run(cmd, env=env, check=True, timeout=timeout)
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
        subprocess.run(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=timeout,
        )

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


def run_system_update(skip_backup: bool = False, restart_service: bool = True) -> None:
    """
    Update system: git pull, dependencies, migrations, and restart services.
    Automatically rolls back on failure.
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

        # 6) Restart
        if restart_service:
            click.echo("Restarting service...")
            restart("bayanat")
            logger.info("Service restarted")

        logger.info("System update completed successfully")

    except Exception as e:
        # ROLLBACK on any failure
        logger.error(f"Update failed, rolling back: {e}")
        click.echo(f"Update failed: {e}")

        if git_commit_before:
            subprocess.run(
                ["git", "reset", "--hard", git_commit_before], cwd=project_root, check=False
            )
            subprocess.run(["uv", "sync", "--frozen"], cwd=project_root, check=False)
            logger.info(f"Rolled back code to: {git_commit_before[:8]}")

        if backup_file and Path(backup_file).exists():
            # Clean up database connections
            with suppress(Exception):
                db.session.rollback()
                db.session.remove()
                db.engine.dispose()

            # Terminate connections
            with suppress(Exception):
                with db.engine.begin() as conn:
                    conn.execute(
                        text(
                            "SELECT pg_terminate_backend(pid) "
                            "FROM pg_stat_activity "
                            "WHERE datname = :dbname AND pid <> pg_backend_pid()"
                        ),
                        {"dbname": db.engine.url.database},
                    )
                logger.info("Terminated active database connections")

            # Restore database (don't suppress errors)
            try:
                restore_backup(backup_file, timeout=600)
                logger.info(f"Database restored from: {backup_file}")
            except Exception as restore_error:
                logger.error(f"Database rollback failed: {restore_error}")

        if restart_service:
            restart("bayanat")
            logger.info("Service restarted after rollback")

        raise RuntimeError(f"Update failed and rolled back: {e}")
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
    """CLI entry point that delegates to the shared update implementation."""
    run_system_update(skip_backup=skip_backup)
