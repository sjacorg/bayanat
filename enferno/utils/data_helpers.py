from typing import Optional
import pandas as pd
from hashlib import md5

from enferno.admin.models import (
    ClaimedViolation,
    Eventtype,
    LocationAdminLevel,
    LocationType,
    PotentialViolation,
    AtobInfo,
    BtobInfo,
    AtoaInfo,
    ItobInfo,
    ItoaInfo,
    ItoiInfo,
    Country,
    Ethnography,
    MediaCategory,
    GeoLocationType,
    WorkflowStatus,
)
from enferno.extensions import db
from enferno.admin.models import (
    Media,
    ClaimedViolation,
    Eventtype,
    LocationAdminLevel,
    LocationType,
    PotentialViolation,
)
from enferno.data_import.models import DataImport
from enferno.user.models import Role
from enferno.utils.logging_utils import get_logger
import enferno.utils.typing as t

from sqlalchemy import and_, or_

logger = get_logger()


def get_file_hash(filepath: str) -> str:
    """
    Returns a file md5 hash.

    Args:
        - filepath: The path to the file to hash.

    Returns:
        - The md5 hash of the file.
    """
    with open(filepath, "rb") as file_check:
        file_read = file_check.read()
        etag = md5(file_read).hexdigest()
    return etag


def media_check_duplicates(etag: str, data_import_id: Optional[t.id] = None) -> bool:
    """
    Checks for duplicate media files.

    Args:
        - etag: The md5 hash of the file.
        - data_import_id: The id of the data import.

    Returns:
        - bool: True if the media file exists, False otherwise.
    """
    exists = False
    # checking for existing media or pending or processing imports
    exists = (
        Media.query.filter(Media.etag == etag, Media.deleted is not True).first()
        or DataImport.query.filter(
            and_(
                DataImport.id != data_import_id,
                DataImport.file_hash == etag,
                or_(DataImport.status == "Pending", DataImport.status == "Processing"),
            )
        ).first()
    )
    return exists


def generate_user_roles() -> None:
    """
    Generates standard user roles.
    """
    # create admin role if it doesn't exist
    r = Role.query.filter_by(name="Admin").first()
    if not r:
        role = Role()
        role.name = "Admin"
        role.description = "System Role"
        role.save()

    # create DA role, if not exists
    r = Role.query.filter_by(name="DA").first()
    if not r:
        role = Role()
        role.name = "DA"
        role.description = "System Role"
        role.save()

    # create MOD role, if not exists
    r = Role.query.filter_by(name="Mod").first()
    if not r:
        role = Role()
        role.name = "Mod"
        role.description = "System Role"
        role.save()


def generate_workflow_statues() -> None:
    """
    Generates system workflow statues.
    """
    if not WorkflowStatus.query.all():
        statuses = [
            "Machine Created",
            "Human Created",
            "Updated",
            "Peer Reviewed",
            "Finalized",
            "Senior Reviewed",
            "Machine Updated",
            "Assigned",
            "Second Peer Review",
            "Revisited",
            "Senior Updated",
            "Peer Review Assigned",
        ]

        for status in statuses:
            db.session.add(WorkflowStatus(title=status, title_tr=status))
        db.session.commit()


def import_default_data() -> None:
    """
    Imports SJAC data from data dir.
    """
    items = [
        (Eventtype, "enferno/data/eventtypes.csv"),
        (PotentialViolation, "enferno/data/potential_violation.csv"),
        (ClaimedViolation, "enferno/data/claimed_violation.csv"),
        (AtobInfo, "enferno/data/atob_info.csv"),
        (BtobInfo, "enferno/data/btob_info.csv"),
        (AtoaInfo, "enferno/data/atoa_info.csv"),
        (ItobInfo, "enferno/data/itob_info.csv"),
        (ItoaInfo, "enferno/data/itoa_info.csv"),
        (ItoiInfo, "enferno/data/itoi_info.csv"),
        (Country, "enferno/data/countries.csv"),
        (MediaCategory, "enferno/data/media_categories.csv"),
        (GeoLocationType, "enferno/data/geo_location_types.csv"),
    ]

    for model, path in items:
        import_csv_to_table(model, path)


def create_default_location_data() -> None:
    """
    Generates default required location data.
    """
    if not LocationAdminLevel.query.all():
        db.session.add(LocationAdminLevel(code=1, title="Governorate"))
        db.session.add(LocationAdminLevel(code=2, title="District"))
        db.session.add(LocationAdminLevel(code=3, title="Subdistrict"))
        db.session.add(LocationAdminLevel(code=4, title="Community"))
        db.session.add(LocationAdminLevel(code=5, title="Neighbourhood"))
        db.session.commit()

    if not LocationType.query.all():
        db.session.add(LocationType(title="Administrative Location"))
        db.session.add(LocationType(title="Point of Interest"))
        db.session.commit()


def import_csv_to_table(model: t.Model, csv_file_path: str) -> None:
    """
    Imports CSV data into a database model.

    Args:
        - model: The SQLAlchemy model to import data into.
        - csv_file_path: The path to the CSV file to import.
    """
    df = pd.read_csv(csv_file_path, parse_dates=True, na_filter=False)

    # Remove the 'deleted' column from DataFrame if it exists
    df.drop(columns=["deleted"], errors="ignore", inplace=True)

    # Skip if model table already contains data
    if db.session.query(model).first():
        logger.info(f"{model.__name__} table already populated.")
        return

    # Add each row as a record in the model table
    for _, row in df.iterrows():
        data = {col: row[col] for col in row.index if hasattr(model, col)}
        db.session.add(model(**data))

    db.session.commit()
    logger.info(f"Data imported into {model.__name__}.")

    # reset id sequence counter
    table = model.__table__
    query = db.select(db.func.max(table.c.id) + 1)
    max_id = db.session.scalar(query)
    sequence_name = f"{table.name}_id_seq"

    stmt = db.text("SELECT format('%I', :seq)")
    quoted_seq = db.session.scalar(stmt, {"seq": sequence_name})

    stmt = db.text(f"ALTER SEQUENCE {quoted_seq} RESTART WITH :val")
    db.session.execute(stmt, {"val": max_id or 1})
    db.session.commit()
    logger.info(f"{model.__name__} ID counter updated.")
