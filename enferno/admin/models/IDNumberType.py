from enferno.extensions import db
from enferno.utils.base import ComponentDataMixin

from enferno.utils.logging_utils import get_logger
from sqlalchemy import text

logger = get_logger()


class IDNumberType(db.Model, ComponentDataMixin):
    __tablename__ = "id_number_types"

    def get_ref_count(self) -> int:
        """
        Get the count of actors that reference this ID number type.

        Returns:
            int: Number of actors that have this ID number type in their id_number array
        """

        result = db.session.execute(
            text(
                """
                SELECT COUNT(*) 
                FROM actor 
                WHERE jsonb_array_length(id_number) > 0 
                AND EXISTS (
                    SELECT 1 
                    FROM jsonb_array_elements(id_number) AS elem 
                    WHERE elem->>'type' = :id_type
                )
            """
            ),
            {"id_type": str(self.id)},
        ).scalar()

        return result or 0
