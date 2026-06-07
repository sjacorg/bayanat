from typing import Any

from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.date_helper import DateHelper


class MediaRedaction(db.Model, BaseMixin):
    __tablename__ = "media_redaction"

    id = db.Column(db.Integer, primary_key=True)
    source_media_id = db.Column(
        db.Integer,
        db.ForeignKey("media.id"),
        nullable=False,
        index=True,
    )
    result_media_id = db.Column(
        db.Integer,
        db.ForeignKey("media.id"),
        nullable=False,
        index=True,
    )
    regions = db.Column(db.JSON, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), index=True)

    source_media = db.relationship("Media", foreign_keys=[source_media_id])
    result_media = db.relationship("Media", foreign_keys=[result_media_id])

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_media_id": self.source_media_id,
            "result_media_id": self.result_media_id,
            "regions": self.regions,
            "user_id": self.user_id,
            "created_at": DateHelper.serialize_datetime(self.created_at),
        }
