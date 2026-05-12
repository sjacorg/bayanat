# -*- coding: utf-8 -*-
"""Click commands."""

import os
from datetime import datetime, timezone

import click
from flask import current_app
from flask.cli import AppGroup, with_appcontext
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
from enferno.admin.models.DynamicFormHistory import DynamicFormHistory
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

    # Load SQL functions before create_all (needed by generated columns)
    from enferno.utils.db_utils import ensure_sql_functions

    ensure_sql_functions()

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
        user.set_password(password)
        user.save()
        click.echo("User password has been reset successfully.")
        logger.info("User password has been reset successfully.")
        if not user.active:
            click.echo("Warning: User is not active!")
            logger.warning("User is not active!")


@click.command()
@click.option("--output", "-o", default="password_reset.txt", help="Output file for credentials")
@click.option("--dry-run", is_flag=True, help="Preview without making changes")
@click.option("--bcrypt-only", is_flag=True, help="Only reset users with bcrypt hashes")
@click.option("--active-only", is_flag=True, help="Only reset active users")
@with_appcontext
def reset_all_passwords(output: str, dry_run: bool, bcrypt_only: bool, active_only: bool) -> None:
    """
    Reset all user passwords to random secure values.

    Generates random passwords, updates all users, sets force-reset flag,
    and outputs credentials to a file for admin distribution.
    """
    import secrets
    import string

    def generate_password(length: int = 16) -> str:
        """Generate a secure random password."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    query = User.query
    if active_only:
        query = query.filter(User.active == True)
    users = query.all()
    if not users:
        click.echo("No users found.")
        return

    results = []
    for user in users:
        # Skip users with argon2 hashes if bcrypt-only flag is set
        if bcrypt_only and user.password and user.password.startswith("$argon2"):
            continue

        new_password = generate_password()
        results.append((user.username, user.email, new_password))

        if not dry_run:
            user.set_password(new_password)
            user.set_security_reset_key()
            user.save()

    if dry_run:
        click.echo(f"DRY RUN - Would reset {len(results)} users:")
        for username, email, _ in results:
            click.echo(f"  - {username} ({email})")
        return

    # Write credentials to output file
    with open(output, "w") as f:
        f.write("# Password Reset Credentials\n")
        f.write(f"# Generated: {datetime.now(timezone.utc).isoformat()}\n")
        f.write("# DISTRIBUTE SECURELY AND DELETE THIS FILE AFTER\n\n")
        for username, email, password in results:
            f.write(f"Username: {username}\n")
            f.write(f"Email: {email}\n")
            f.write(f"Password: {password}\n")
            f.write("-" * 40 + "\n")

    click.echo(f"Reset {len(results)} user passwords.")
    click.echo(f"Credentials saved to: {output}")
    click.echo("IMPORTANT: Distribute credentials securely and delete the file after!")
    logger.info(f"Reset passwords for {len(results)} users. Credentials saved to {output}")


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
def doctor() -> None:
    """Run diagnostics on the Bayanat installation."""
    passed = 0
    warnings = 0
    failed = 0

    def ok(msg):
        nonlocal passed
        click.echo(f"  + {msg}")
        passed += 1

    def warn(msg):
        nonlocal warnings
        click.echo(click.style(f"  ! {msg}", fg="yellow"))
        warnings += 1

    def fail(msg):
        nonlocal failed
        click.echo(click.style(f"  - {msg}", fg="red"))
        failed += 1

    # --- Database ---
    click.echo("\nDatabase:")

    try:
        db.session.execute(text("SELECT 1"))
        ok("PostgreSQL connected")
    except Exception as e:
        fail(f"PostgreSQL connection failed: {e}")

    try:
        result = db.session.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'postgis'")
        ).scalar()
        if result:
            ok("PostGIS loaded")
        else:
            fail("PostGIS extension not installed")
    except Exception:
        fail("Could not check PostGIS")

    try:
        result = db.session.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")
        ).scalar()
        if result:
            ok("pg_trgm loaded")
        else:
            fail("pg_trgm extension not installed")
    except Exception:
        fail("Could not check pg_trgm")

    # Alembic migration status
    try:
        import logging as _logging

        from alembic.migration import MigrationContext
        from alembic.script import ScriptDirectory
        from enferno.extensions import migrate as migrate_ext

        # Suppress Alembic's "Context impl" info lines
        _logging.getLogger("alembic.runtime.migration").setLevel(_logging.WARNING)

        config = migrate_ext.get_config()
        script = ScriptDirectory.from_config(config)
        head = script.get_current_head()

        context = MigrationContext.configure(db.session.connection())
        current = context.get_current_heads()
        current_rev = current[0] if current else None

        if current_rev is None:
            warn("No Alembic revision stamped (run: flask db upgrade)")
        elif current_rev == head:
            ok("Migrations up to date")
        else:
            fail(f"Pending migrations (current: {current_rev[:8]}, head: {head[:8]})")
    except Exception as e:
        warn(f"Could not check migrations: {e}")

    # Schema alignment (lightweight check)
    try:
        import warnings as _warnings

        _warnings.filterwarnings("ignore", message="Did not recognize type")
        checker = DBAlignmentChecker()
        issues = []
        for model, table_name in checker.model_classes:
            table = checker.metadata.tables.get(table_name)
            if table is None:
                issues.append(f"missing table '{table_name}'")
                continue
            model_cols = {c.name for c in model.__table__.columns}
            table_cols = {c.name for c in table.columns}
            missing = model_cols - table_cols
            if missing:
                issues.append(f"'{table_name}' missing: {', '.join(missing)}")
        if issues:
            fail(f"Schema mismatch: {'; '.join(issues[:3])}")
        else:
            ok("Schema aligned with models")
    except Exception as e:
        warn(f"Could not check schema: {e}")

    # --- Services ---
    click.echo("\nServices:")

    try:
        from enferno.extensions import rds

        rds.ping()
        ok("Redis connected")
    except Exception:
        fail("Redis not reachable")

    try:
        from enferno.tasks import celery

        inspector = celery.control.inspect(timeout=2)
        ping = inspector.ping()
        if ping:
            worker_count = len(ping)
            ok(f"Celery workers responding ({worker_count})")
        else:
            warn("No Celery workers responding")
    except Exception:
        warn("Could not reach Celery workers")

    # --- Filesystem ---
    click.echo("\nFilesystem:")

    media_dir = os.path.join(current_app.config.get("APP_DIR", "enferno"), "media")
    if os.path.isdir(media_dir) and os.access(media_dir, os.W_OK):
        ok("Media directory OK")
    elif os.path.isdir(media_dir):
        warn("Media directory exists but not writable")
    else:
        fail("Media directory missing")

    logs_dir = os.path.join(Config.PROJECT_ROOT, "logs")
    if os.path.isdir(logs_dir) and os.access(logs_dir, os.W_OK):
        ok("Logs directory OK")
    elif os.path.isdir(logs_dir):
        warn("Logs directory exists but not writable")
    else:
        warn("Logs directory missing")

    env_path = os.path.join(Config.PROJECT_ROOT, ".env")
    if os.path.isfile(env_path):
        ok(".env file exists")
    else:
        fail(".env file missing")

    # --- Config ---
    click.echo("\nConfig:")

    secret_key = current_app.config.get("SECRET_KEY")
    if secret_key and secret_key != "test-secret-key-not-for-production":
        ok("SECRET_KEY set")
    elif secret_key:
        warn("SECRET_KEY is using test default")
    else:
        fail("SECRET_KEY not set")

    salt = current_app.config.get("SECURITY_PASSWORD_SALT")
    if salt and salt != "test-salt":
        ok("SECURITY_PASSWORD_SALT set")
    elif salt:
        warn("SECURITY_PASSWORD_SALT is using test default")
    else:
        fail("SECURITY_PASSWORD_SALT not set")

    mail_server = current_app.config.get("MAIL_SERVER")
    if mail_server:
        ok(f"Mail configured ({mail_server})")
    else:
        warn("MAIL_SERVER not configured")

    # --- Summary ---
    click.echo(f"\n{passed} passed", nl=False)
    if warnings:
        click.echo(click.style(f", {warnings} warnings", fg="yellow"), nl=False)
    if failed:
        click.echo(click.style(f", {failed} failed", fg="red"), nl=False)
    click.echo()

    raise SystemExit(1 if failed else 0)


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
@click.option("--all", "process_all", is_flag=True, help="Process all pending media")
@click.option("--bulletin-ids", "-b", help="Comma-separated bulletin IDs")
@click.option("--label", help="Filter by bulletin label ID or title")
@click.option("--role", help="Filter by bulletin access role ID or name")
@click.option("--limit", "-n", type=int, help="Maximum number of media to process")
@click.option(
    "--language",
    "-l",
    multiple=True,
    default=["ar", "en"],
    help="Language hints (can specify multiple)",
)
@click.option("--force", "-f", is_flag=True, help="Re-process media that already have extractions")
@with_appcontext
def process(
    process_all: bool,
    bulletin_ids: str,
    label: str,
    role: str,
    limit: int,
    language: tuple,
    force: bool,
) -> None:
    """Batch process media files for OCR extraction via Celery."""
    from sqlalchemy import or_

    from enferno.admin.models import Media, Extraction, Bulletin
    from enferno.admin.models.tables import bulletin_labels, bulletin_roles
    from enferno.tasks import bulk_ocr_process

    # Build query for media
    query = db.session.query(Media.id)
    if not force:
        query = query.outerjoin(Extraction).filter(Extraction.id.is_(None))

    # Only include OCR-supported file types
    ocr_ext = current_app.config.get("OCR_EXT", [])
    if ocr_ext:
        query = query.filter(or_(*[Media.media_file.ilike(f"%.{ext}") for ext in ocr_ext]))

    if bulletin_ids:
        ids = [int(x.strip()) for x in bulletin_ids.split(",")]
        query = query.filter(Media.bulletin_id.in_(ids))

    # Join Bulletin once if filtering by label or role
    if label or role:
        query = query.join(Bulletin, Media.bulletin_id == Bulletin.id)

    if label:
        from enferno.admin.models import Label

        label_obj = Label.query.filter(
            (Label.id == int(label)) if label.isdigit() else (Label.title == label)
        ).first()
        if not label_obj:
            click.echo(f"Label not found: {label}")
            return
        query = query.join(bulletin_labels, Bulletin.id == bulletin_labels.c.bulletin_id).filter(
            bulletin_labels.c.label_id == label_obj.id
        )
        click.echo(f"Filtering by label: {label_obj.title} (id={label_obj.id})")

    if role:
        from enferno.user.models import Role

        role_obj = Role.query.filter(
            (Role.id == int(role)) if role.isdigit() else (Role.name == role)
        ).first()
        if not role_obj:
            click.echo(f"Role not found: {role}")
            return
        query = query.join(bulletin_roles, Bulletin.id == bulletin_roles.c.bulletin_id).filter(
            bulletin_roles.c.role_id == role_obj.id
        )
        click.echo(f"Filtering by role: {role_obj.name} (id={role_obj.id})")

    if not process_all and not bulletin_ids and not label and not role and not limit:
        click.echo("Error: Specify --all, --bulletin-ids, --label, --role, or --limit")
        return

    if limit:
        query = query.limit(limit)

    media_ids = [row[0] for row in query.all()]

    if not media_ids:
        click.echo("No pending media found")
        return

    bulk_ocr_process(media_ids, language_hints=list(language), force=force)
    click.echo(f"Queued {len(media_ids)} media files for OCR processing.")


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
@click.option("--force", "-f", is_flag=True, help="Re-process even if extraction exists")
@with_appcontext
def extract(media_id: int, language: tuple, show_text: bool, force: bool) -> None:
    """Extract text from a media file using Google Vision OCR."""
    from enferno.admin.models import Extraction
    from enferno.tasks.extraction import process_media_extraction_task

    click.echo(f"Extracting text from media {media_id}...")
    result = process_media_extraction_task(media_id, list(language), force=force)

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

    click.echo("\nOCR Status Summary")
    click.echo(f"{'─' * 40}")
    click.echo(f"Total media:          {total_media:,}")
    click.echo(f"Pending (no OCR):     {pending:,}")
    click.echo(f"{'─' * 40}")

    for status_name in ["processed", "failed", "cant_read"]:
        data = status_map.get(status_name, {"count": 0, "avg_conf": None})
        count = data["count"]
        avg = data["avg_conf"]
        conf_str = f" (avg {avg:.1f}%)" if avg else ""
        click.echo(f"{status_name:21} {count:,}{conf_str}")

    click.echo(f"{'─' * 40}")
    click.echo(f"Total extracted:      {total_extracted:,}\n")
