# -*- coding: utf-8 -*-
"""Click commands."""

import os
from datetime import datetime, timezone

import click
from flask import current_app
from flask.cli import AppGroup, with_appcontext
from flask_security.utils import hash_password

from enferno.settings import Config
import json
import shutil
from pathlib import Path

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
from geoalchemy2.shape import to_shape
from sqlalchemy import text
from sqlalchemy.orm import joinedload, subqueryload
from enferno.admin.models import Bulletin, Label
from enferno.admin.models.Media import Media
from enferno.admin.models.tables import bulletin_labels
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
        user.password = hash_password(password)
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
            user.password = hash_password(new_password)
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

    click.echo(f"\nOCR Status Summary")
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


# Public archive export commands
export_cli = AppGroup("export", short_help="Export commands for public archive")

MEDIA_DIR = Media.media_dir


def serialize_bulletin(bulletin):
    """Serialize a bulletin for the public archive export.

    Includes only public-facing fields. Strips workflow, assignment,
    review, and internal metadata.
    """
    labels = [
        {"id": l.id, "title": l.title, "title_ar": l.title_ar, "verified": l.verified}
        for l in bulletin.labels
    ]

    ver_labels = [
        {"id": l.id, "title": l.title, "title_ar": l.title_ar} for l in bulletin.ver_labels
    ]

    sources = [{"id": s.id, "title": s.title} for s in bulletin.sources]

    locations = [
        {
            "id": loc.id,
            "title": loc.title,
            "title_ar": loc.title_ar,
            "lat": to_shape(loc.latlng).y if loc.latlng else None,
            "lng": to_shape(loc.latlng).x if loc.latlng else None,
            "location_type": loc.location_type.title if loc.location_type else None,
            "country": loc.country.title if loc.country else None,
            "full_location": loc.full_location,
        }
        for loc in bulletin.locations
    ]

    geo_locations = [
        {
            "id": geo.id,
            "title": geo.title,
            "lat": to_shape(geo.latlng).y if geo.latlng else None,
            "lng": to_shape(geo.latlng).x if geo.latlng else None,
            "type": geo.type.title if geo.type else None,
        }
        for geo in bulletin.geo_locations
    ]

    events = [
        {
            "id": e.id,
            "title": e.title,
            "title_ar": e.title_ar,
            "type": e.eventtype.title if e.eventtype else None,
            "from_date": DateHelper.serialize_datetime(e.from_date),
            "to_date": DateHelper.serialize_datetime(e.to_date),
            "location": e.location.title if e.location else None,
        }
        for e in bulletin.events
    ]

    medias = []
    for media in bulletin.medias:
        if media.deleted:
            continue
        entry = {
            "id": media.id,
            "filename": media.media_file,
            "type": media.media_file_type,
            "title": media.title,
            "title_ar": media.title_ar,
        }
        if media.extraction:
            entry["extraction"] = {
                "text": media.extraction.text,
                "original_text": media.extraction.original_text,
                "confidence": media.extraction.confidence,
                "language": media.extraction.language,
            }
        medias.append(entry)

    related_bulletins = []
    for rel in bulletin.bulletin_relations:
        other = rel.bulletin_to if bulletin.id == rel.bulletin_id else rel.bulletin_from
        related_bulletins.append(
            {
                "id": other.id,
                "title": other.title,
                "title_ar": other.title_ar,
                "related_as": rel.related_as,
            }
        )

    related_actors = [
        {
            "id": rel.actor.id,
            "name": rel.actor.name,
            "type": rel.actor.type,
            "related_as": rel.related_as or [],
        }
        for rel in bulletin.related_actors
    ]

    related_incidents = [
        {
            "id": rel.incident.id,
            "title": rel.incident.title,
            "title_ar": rel.incident.title_ar,
            "related_as": rel.related_as,
        }
        for rel in bulletin.related_incidents
    ]

    return {
        "id": bulletin.id,
        "title": bulletin.title,
        "title_ar": bulletin.title_ar,
        "description": bulletin.description,
        "source_link": bulletin.source_link,
        "publish_date": DateHelper.serialize_datetime(bulletin.publish_date),
        "documentation_date": DateHelper.serialize_datetime(bulletin.documentation_date),
        "labels": labels,
        "verified_labels": ver_labels,
        "sources": sources,
        "locations": locations,
        "geo_locations": geo_locations,
        "events": events,
        "media": medias,
        "related_bulletins": related_bulletins,
        "related_actors": related_actors,
        "related_incidents": related_incidents,
    }


def copy_media_files(bulletins, output_dir):
    """Copy media files for exported bulletins to the output directory.

    Reads FILESYSTEM_LOCAL from app config to decide between local copy and S3 download.
    """
    import boto3

    cfg = current_app.config
    use_s3 = not cfg.get("FILESYSTEM_LOCAL")
    dest_dir = output_dir / "media"
    dest_dir.mkdir(exist_ok=True)

    s3 = None
    if use_s3:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=cfg["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=cfg["AWS_SECRET_ACCESS_KEY"],
            region_name=cfg["AWS_REGION"],
        )

    copied = 0
    missing = 0
    for bulletin in bulletins:
        for media in bulletin.medias:
            if media.deleted or not media.media_file:
                continue
            dest = dest_dir / media.media_file
            if use_s3:
                try:
                    s3.download_file(cfg["S3_BUCKET"], media.media_file, str(dest))
                    copied += 1
                except Exception:
                    logger.warning(
                        "S3 download failed: %s (bulletin %d)", media.media_file, bulletin.id
                    )
                    missing += 1
            else:
                src = MEDIA_DIR / media.media_file
                if src.exists():
                    shutil.copy2(src, dest)
                    copied += 1
                else:
                    logger.warning("Media file not found: %s (bulletin %d)", src, bulletin.id)
                    missing += 1

    return copied, missing


@export_cli.command("public")
@click.option("--label", required=True, help="Label title to filter bulletins for export.")
@click.option("--output", required=True, type=click.Path(), help="Output directory for the export.")
@click.option("--copy-media/--no-copy-media", default=True, help="Copy media files to output.")
@with_appcontext
def export_public(label, output, copy_media):
    """Export labeled bulletins as denormalized JSON for the public archive.

    Usage:
        flask export public --label "public-archive" --output ./export/
    """
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    target_label = Label.query.filter(Label.title == label).first()
    if not target_label:
        click.echo(f'Label "{label}" not found.')
        raise SystemExit(1)

    bulletins = (
        Bulletin.query.join(bulletin_labels)
        .filter(bulletin_labels.c.label_id == target_label.id)
        .filter(Bulletin.deleted == False)
        .options(
            subqueryload(Bulletin.labels),
            subqueryload(Bulletin.ver_labels),
            subqueryload(Bulletin.sources),
            subqueryload(Bulletin.locations),
            subqueryload(Bulletin.geo_locations),
            subqueryload(Bulletin.events),
            subqueryload(Bulletin.medias).joinedload(Media.extraction),
            subqueryload(Bulletin.bulletins_to),
            subqueryload(Bulletin.bulletins_from),
            subqueryload(Bulletin.related_actors),
            subqueryload(Bulletin.related_incidents),
        )
        .order_by(Bulletin.id)
        .all()
    )

    if not bulletins:
        click.echo(f'No bulletins found with label "{label}".')
        raise SystemExit(1)

    click.echo(f"Exporting {len(bulletins)} bulletins...")

    documents = [serialize_bulletin(b) for b in bulletins]

    out_file = output_dir / "documents.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)
    click.echo(f"Wrote {len(documents)} documents to {out_file}")

    if copy_media:
        copied, missing = copy_media_files(bulletins, output_dir)
        click.echo(f"Copied {copied} media files ({missing} missing)")

    click.echo("Export complete.")
