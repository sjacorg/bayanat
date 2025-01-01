from enferno.extensions import db
from enferno.utils.base import BaseMixin

from enferno.utils.logging_utils import get_logger

logger = get_logger()


class Settings(db.Model, BaseMixin):
    """User Specific Settings. (SQL Alchemy model)"""

    id = db.Column(db.Integer, primary_key=True)
    darkmode = db.Column(db.Boolean, default=False)
