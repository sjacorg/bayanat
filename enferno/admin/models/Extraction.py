"""Text extraction results from OCR processing."""

from enferno.extensions import db


class Extraction(db.Model):
    """OCR extraction result linked 1:1 with Media."""

    __tablename__ = "extraction"

    id = db.Column(db.Integer, primary_key=True)
    media_id = db.Column(db.Integer, db.ForeignKey("media.id"), unique=True, nullable=False)

    text = db.Column(db.Text)
    raw = db.Column(db.JSON)
    confidence = db.Column(db.Float)
    orientation = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="pending", nullable=False)
    manual = db.Column(db.Boolean, default=False, nullable=False)

    reviewed_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    reviewed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)

    media = db.relationship("Media", backref=db.backref("extraction", uselist=False), uselist=False)
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])

    def to_dict(self):
        return {
            "id": self.id,
            "media_id": self.media_id,
            "text": self.text,
            "confidence": self.confidence,
            "orientation": self.orientation,
            "status": self.status,
            "manual": self.manual,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
