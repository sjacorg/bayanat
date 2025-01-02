import json
import pathlib
from datetime import datetime
from pathlib import Path
from typing import Any

from werkzeug.utils import secure_filename

from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger
from enferno.admin.models.MediaCategory import MediaCategory
from enferno.admin.models.utils import check_roles

logger = get_logger()


class Media(db.Model, BaseMixin):
    """
    SQL Alchemy model for media
    """

    # __table_args__ = {"extend_existing": True}

    extend_existing = True

    __table_args__ = (
        db.Index(
            "ix_media_etag_unique_not_deleted",
            "etag",
            unique=True,
            postgresql_where=db.text("deleted = FALSE"),
        ),
    )

    # set media directory here (could be set in the settings)
    media_dir = Path("enferno/media")
    inline_dir = Path("enferno/media/inline")
    id = db.Column(db.Integer, primary_key=True)
    media_file = db.Column(db.String, nullable=False)
    media_file_type = db.Column(db.String, nullable=False)
    category = db.Column(db.Integer)
    etag = db.Column(db.String, index=True)
    duration = db.Column(db.String)

    title = db.Column(db.String)
    title_ar = db.Column(db.String)
    comments = db.Column(db.String)
    comments_ar = db.Column(db.String)
    search = db.Column(
        db.Text,
        db.Computed(
            """
            CAST(id AS TEXT) || ' ' ||
            COALESCE(title, '') || ' ' ||
            COALESCE(media_file, '') || ' ' ||
            COALESCE(media_file_type, '') || ' ' ||
            COALESCE(comments, '')
            """
        ),
    )

    time = db.Column(db.Float(precision=2))

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_medias", foreign_keys=[user_id])

    bulletin_id = db.Column(db.Integer, db.ForeignKey("bulletin.id"))
    bulletin = db.relationship("Bulletin", backref="medias", foreign_keys=[bulletin_id])

    actor_id = db.Column(db.Integer, db.ForeignKey("actor.id"))
    actor = db.relationship("Actor", backref="medias", foreign_keys=[actor_id])

    main = db.Column(db.Boolean, default=False)

    # custom serialization method
    @check_roles
    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the media."""
        media_category = MediaCategory.query.get(self.category) if self.category else None
        return {
            "id": self.id,
            "title": self.title if self.title else None,
            "title_ar": self.title_ar if self.title_ar else None,
            "category": media_category.to_dict() if media_category else None,
            "fileType": self.media_file_type if self.media_file_type else None,
            "filename": self.media_file if self.media_file else None,
            "etag": getattr(self, "etag", None),
            "time": getattr(self, "time", None),
            "duration": self.duration,
            "main": self.main,
            "updated_at": DateHelper.serialize_datetime(self.updated_at)
            if self.updated_at
            else None,
        }

    def to_json(self) -> str:
        """Return a JSON representation of the media."""
        return json.dumps(self.to_dict())

    # populates model from json dict
    def from_json(self, json: dict[str, Any]) -> "Media":
        """
        Create a media object from a json dictionary.

        Args:
            - json: the json dictionary to create the media from.

        Returns:
            - the media object.
        """
        self.title = json["title"] if "title" in json else None
        self.title_ar = json["title_ar"] if "title_ar" in json else None
        self.media_file_type = json["fileType"] if "fileType" in json else None
        self.media_file = json["filename"] if "filename" in json else None
        self.etag = json.get("etag", None)
        self.time = json.get("time", None)
        category = json.get("category", None)
        if category:
            self.category = category.get("id")
        return self

    # generate custom file name for upload purposes
    @staticmethod
    def generate_file_name(filename: str) -> str:
        """
        Generate a secure and timestamped file name.

        Args:
            - filename: the original file name.

        Returns:
            - the generated file name.
        """
        return "{}-{}".format(
            datetime.utcnow().strftime("%Y%m%d-%H%M%S"),
            secure_filename(filename).lower(),
        )

    @staticmethod
    def validate_file_extension(filepath: str, allowed_extensions: list[str]) -> bool:
        """
        Validate file extension against a list of allowed extensions.

        Args:
            - filepath: the path to the file.
            - allowed_extensions: list of allowed file extensions.

        Returns:
            - True if extension is valid, False otherwise.
        """
        extension = pathlib.Path(filepath).suffix.lower().lstrip(".")
        return extension in allowed_extensions


# Structure is copied over from previous system
