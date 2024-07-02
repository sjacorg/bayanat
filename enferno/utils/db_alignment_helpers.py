import logging
from typing import Any
from sqlalchemy import create_engine, MetaData
from enferno.settings import Config as cfg
from enferno.extensions import db
import enferno.utils.typing as t

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger()


class DBAlignmentChecker:
    """Class to check the alignment of the database with the models."""

    def __init__(self):
        self.engine = create_engine(cfg.SQLALCHEMY_DATABASE_URI)
        self.metadata = MetaData(bind=self.engine)
        self.metadata.reflect(self.engine)
        self.model_classes = self._get_model_classes()
        self.db_tables = set(self.metadata.tables.keys())
        self.joint_tables = self._get_joint_tables()

    def _type_check(self, model_type: Any, db_type: Any) -> bool:
        """
        Check if the model type and the database type are compatible.

        Args:
            - model_type (Any): The type of the model column.
            - db_type (Any): The type of the database column.

        Returns:
            - bool: True if the types are compatible, False otherwise.
        """
        return isinstance(model_type, type(db_type)) or isinstance(db_type, type(model_type))

    def _get_model_classes(self) -> list:
        """Return a list of all model classes and their table names."""
        return [(model, model.__tablename__) for model in db.Model.__subclasses__()]

    def _get_joint_tables(self) -> set:
        """Return a set of all joint tables in the database."""
        joint_tables = set()
        for model, _ in self.model_classes:
            for attr in dir(model):
                if attr.startswith("_"):
                    continue
                field = getattr(model, attr)
                if hasattr(field, "property") and hasattr(field.property, "mapper"):
                    # Check if it's a relationship and a secondary table is involved
                    if field.property.secondary is not None:
                        joint_tables.add(field.property.secondary.name)
        return joint_tables

    def _report_table_discrepancies(self, model: t.Model, table_name: str) -> bool:
        """
        Report discrepancies between the model and the database table using the following rules:

        1. If the table is missing in the database, log an error, return False.
        2. If a column is missing in the table, log a warning.
        3. If a column type is different in the table, log a warning.
        4. If there are extra columns in the table, log an info message.
        5. Return true if no errors are found (will return True with warnings and info messages).

        Args:
            - model (Model): The model class to compare.
            - table_name (str): The name of the table in the database.

        Returns:
            - bool: True if the model and table are aligned, False otherwise.
        """
        table = self.metadata.tables.get(table_name)
        if table is None:
            logger.error(f"Table '{table_name}' for model {model.__name__} does not exist")
            return False

        model_columns = {c.name: c.type for c in model.__table__.columns}
        table_columns = {c.name: c.type for c in table.columns}

        for name, model_type in model_columns.items():
            if name not in table_columns:
                logger.warning(f"Column '{name}' missing in table '{table_name}'.")
            elif not self._type_check(model_type, table_columns[name]):
                logger.warning(
                    f"Type mismatch for '{name}' in table '{table_name}': Model type {model_type} vs. Table type {table_columns[name]}."
                )

        for name in table_columns:
            if name not in model_columns:
                logger.info(f"Extra column '{name}' in table '{table_name}', not in model.")

        return True

    def _find_extra_tables(self) -> set:
        """Find extra tables in the database not present in the models."""
        model_tables = {name for _, name in self.model_classes}
        extras = self.db_tables - model_tables - self.joint_tables
        return {t for t in extras if not t.startswith("spatial_")}

    def check_db_alignment(self) -> None:
        """Check the alignment of the database with the models."""
        aligned = True
        for model, table_name in self.model_classes:
            if not self._report_table_discrepancies(model, table_name):
                aligned = False

        extra_tables = self._find_extra_tables()
        if extra_tables:
            logger.info(
                f"Extra tables in database not present in models: {', '.join(extra_tables)}"
            )

        if aligned:
            logger.info("The database is aligned with the schema")
