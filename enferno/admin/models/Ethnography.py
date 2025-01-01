from enferno.extensions import db
from enferno.utils.base import ComponentDataMixin

from enferno.utils.logging_utils import get_logger

logger = get_logger()


class Ethnography(db.Model, ComponentDataMixin):
    __tablename__ = "ethnographies"
