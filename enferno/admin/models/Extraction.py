"""Text extraction results from OCR processing."""

from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.date_helper import DateHelper


class Extraction(db.Model, BaseMixin):
    """OCR extraction result linked 1:1 with Media."""

    __tablename__ = "extraction"

    id = db.Column(db.Integer, primary_key=True)
    media_id = db.Column(db.Integer, db.ForeignKey("media.id"), unique=True, nullable=False)

    text = db.Column(db.Text)
    original_text = db.Column(db.Text)
    raw = db.Column(db.JSON)
    confidence = db.Column(db.Float)
    orientation = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="pending", nullable=False)
    manual = db.Column(db.Boolean, default=False, nullable=False)
    word_count = db.Column(db.Integer, default=0)
    language = db.Column(db.String(10))
    search_text = db.Column(
        db.Text,
        db.Computed("normalize_arabic_text(text)"),
    )

    reviewed_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    reviewed_at = db.Column(db.DateTime)

    media = db.relationship("Media", backref=db.backref("extraction", uselist=False), uselist=False)
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])

    def to_dict(self):
        return {
            "id": self.id,
            "media_id": self.media_id,
            "text": self.text,
            "original_text": self.original_text,
            "confidence": self.confidence,
            "orientation": self.orientation,
            "status": self.status,
            "manual": self.manual,
            "word_count": self.word_count,
            "language": self.language,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": DateHelper.serialize_datetime(self.reviewed_at),
            "created_at": DateHelper.serialize_datetime(self.created_at),
            "updated_at": DateHelper.serialize_datetime(self.updated_at),
        }

    def to_compact_dict(self):
        """Metadata only, no text fields. Use for bulk/embedded responses."""
        return {
            "id": self.id,
            "media_id": self.media_id,
            "status": self.status,
            "word_count": self.word_count,
            "language": self.language,
            "confidence": self.confidence,
            "manual": self.manual,
        }
