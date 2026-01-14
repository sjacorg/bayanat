"""Text extraction results from OCR processing."""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from enferno.extensions import db


class Extraction(db.Model):
    """OCR extraction result linked 1:1 with Media."""

    __tablename__ = "extraction"

    id = Column(Integer, primary_key=True)
    media_id = Column(Integer, ForeignKey("media.id"), unique=True, nullable=False)

    text = Column(Text)
    raw = Column(JSONB)
    confidence = Column(Float)
    orientation = Column(Integer, default=0)
    status = Column(String(20), default="pending", nullable=False)

    reviewed_by = Column(Integer, ForeignKey("user.id"))
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    media = relationship("Media", backref="extraction", uselist=False)
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    def to_dict(self):
        return {
            "id": self.id,
            "media_id": self.media_id,
            "text": self.text,
            "confidence": self.confidence,
            "orientation": self.orientation,
            "status": self.status,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
