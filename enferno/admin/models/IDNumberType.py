from enferno.extensions import db
from enferno.utils.base import ComponentDataMixin

from enferno.utils.logging_utils import get_logger

logger = get_logger()


class IDNumberType(db.Model, ComponentDataMixin):
    __tablename__ = "id_number_types"

    def get_ref_count(self) -> int:
        """
        Get the count of actors that reference this ID number type.

        Returns:
            int: Number of actors that have this ID number type in their id_number array
        """
        from enferno.admin.models.Actor import Actor

        return Actor.query.filter(Actor.id_number.op("@>")([{"type": str(self.id)}])).count()
