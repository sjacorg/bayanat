from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    Boolean,
    Float,
    ARRAY as SQLArray,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import text
from enferno.admin.models import Incident
from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.logging_utils import get_logger

logger = get_logger()


class DynamicField(db.Model, BaseMixin):
    """
    Defines custom fields for any entity type.

    JSONB Field Documentation:

    - schema_config (JSONB): Database-related config.
        Example:
        {
            "type": "string",
            "required": true,
            "default": "",
            "unique": false,
            "max_length": 100
        }

    - ui_config (JSONB): UI rendering config.
        Example:
        {
            "label": "Full Name",
            "help_text": "Enter your full legal name.",
            "widget": "text_input",
            "sort_order": 1,
            "readonly": false,
            "hidden": false,
            "group": "personal",
            "group_label": "Personal Info",
            "width": "full"
        }

    - validation_config (JSONB): Validation rules.
        Example:
        {
            "min_length": 2,
            "max_length": 100,
            "pattern": "^[A-Za-z ]+$"
        }

    - options (JSONB): Allowed values for select/multi fields.
        Example:
        [
            {"value": "admin", "label": "Administrator"},
            {"value": "user", "label": "User"}
        ]
    """

    __tablename__ = "dynamic_fields"

    # Field Types
    STRING = "string"
    INTEGER = "integer"
    DATETIME = "datetime"
    ARRAY = "array"
    TEXT = "text"
    BOOLEAN = "boolean"
    FLOAT = "float"
    JSON = "json"

    # UI Components for rendering
    class UIComponent:
        TEXT_INPUT = "text_input"
        TEXT_AREA = "text_area"
        NUMBER = "number"
        DATE_PICKER = "date_picker"
        DROPDOWN = "dropdown"
        MULTI_SELECT = "multi_select"
        CHECKBOX = "checkbox"

    # Field type to UI component mapping
    COMPONENT_MAP = {
        STRING: [UIComponent.TEXT_INPUT, UIComponent.DROPDOWN],
        INTEGER: [UIComponent.NUMBER],
        DATETIME: [UIComponent.DATE_PICKER],
        ARRAY: [UIComponent.MULTI_SELECT],
        TEXT: [UIComponent.TEXT_AREA],
        BOOLEAN: [UIComponent.CHECKBOX],
        FLOAT: [UIComponent.NUMBER],
        JSON: [UIComponent.TEXT_AREA],
    }

    # SQL Type mapping for column creation
    TYPE_MAP = {
        STRING: "character varying",
        INTEGER: "integer",
        DATETIME: "timestamp with time zone",
        ARRAY: "character varying[]",
        TEXT: "text",
        BOOLEAN: "boolean",
        FLOAT: "double precision",
        JSON: "jsonb",
    }

    # SQLAlchemy column types
    _column_types = {
        STRING: String(100),
        INTEGER: Integer,
        DATETIME: DateTime(timezone=True),
        ARRAY: SQLArray(String),
        TEXT: Text,
        BOOLEAN: Boolean,
        FLOAT: Float,
        JSON: JSONB,
    }

    id = db.Column(db.Integer, primary_key=True)  # Primary key
    name = db.Column(db.String(50), nullable=False)  # Python identifier for the field
    title = db.Column(db.String(100), nullable=False)  # Human-readable label
    entity_type = db.Column(
        db.String(50), nullable=False
    )  # Target entity/table (e.g., 'bulletin', 'actor')
    field_type = db.Column(db.String(20), nullable=False)  # Data type of the field
    required = db.Column(
        db.Boolean, default=False
    )  # Whether the field is required (legacy, see schema_config)
    searchable = db.Column(db.Boolean, default=False)  # Whether the field is indexed for search

    # UI Configuration
    ui_component = db.Column(db.String(20))  # How the field should be rendered in the UI
    schema_config = db.Column(
        JSONB, default=dict
    )  # DB-related: type, required, default, unique, etc.
    ui_config = db.Column(
        JSONB, default=dict
    )  # UI-related: label, help_text, widget, sort_order, readonly, hidden, group (string), group_label (optional), width ("full" or "half")
    validation_config = db.Column(
        JSONB, default=dict
    )  # Validation rules: min/max, pattern, allowed values, etc.
    options = db.Column(JSONB, default=list)  # Allowed values for select/multi fields

    active = db.Column(db.Boolean, default=True)  # Whether the field is active

    __table_args__ = (db.UniqueConstraint("name", "entity_type", name="uq_field_name_entity"),)

    def __init__(self, *args, **kwargs):
        self._validated = False
        super().__init__(*args, **kwargs)
        if kwargs:  # Only validate if kwargs are provided
            self.validate_field()
            self._validated = True

    @classmethod
    def get_valid_components(cls, field_type: str) -> list:
        """Get valid UI components for a field type"""
        return cls.COMPONENT_MAP.get(field_type, [])

    def validate_field(self):
        """Validate field configuration"""
        if not self.name:
            return  # Skip validation if name is not set yet

        if not self.name.isidentifier():
            raise ValueError("Field name must be a valid Python identifier")

        if self.name.startswith("_"):
            raise ValueError("Field name cannot start with underscore")

        if not self.entity_type:
            return  # Skip validation if entity_type not set yet

        # Get model class for entity type
        model_class = self.get_entity_model()

        # Check reserved names
        reserved_names = {"id", "created_at", "updated_at", "deleted"} | set(
            model_class.__table__.columns.keys()
        )
        if self.name in reserved_names:
            raise ValueError(f"Field name '{self.name}' is reserved")

        if not self.field_type:
            return  # Skip validation if field_type not set yet

        if not self.is_valid(self.field_type):
            raise ValueError(f"Invalid field type: {self.field_type}")

        # Validate UI component if set
        if self.ui_component and self.ui_component not in self.get_valid_components(
            self.field_type
        ):
            raise ValueError(
                f"Invalid UI component {self.ui_component} for field type {self.field_type}"
            )

        # Validate options if dropdown/multi-select
        if (
            self.ui_component in [self.UIComponent.DROPDOWN, self.UIComponent.MULTI_SELECT]
            and not self.options
        ):
            raise ValueError(f"Options are required for {self.ui_component}")

        # Validate config based on field type
        self.validate_config()

    def get_ui_schema(self) -> dict:
        """Get UI schema for rendering the field"""
        schema = {
            "type": self.field_type,
            "component": self.ui_component or self.get_valid_components(self.field_type)[0],
            "title": self.title,
            "ui_config": self.ui_config,
            "required": self.schema_config.get("required", self.required),
            "schema_config": self.schema_config,
            "validation_config": self.validation_config,
            "options": self.options,
        }
        return schema

    def save(self):
        """Save the field after validating if not already validated"""
        if not self._validated:
            self.validate_field()
            self._validated = True
        return super().save()

    def create_column(self):
        """Create the actual column in the entity table"""
        model_class = self.get_entity_model()
        table_name = model_class.__tablename__

        try:
            sql_type = DynamicField.TYPE_MAP[self.field_type]
            if not sql_type:
                raise ValueError(f"Invalid field type: {self.field_type}")

            constraints = []
            if self.required:
                constraints.append("NOT NULL")

            full_sql_type = f"{sql_type} {' '.join(constraints)}".strip()

            # Execute DDL for column creation
            db.session.execute(
                text(
                    f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {self.name} {full_sql_type}"
                )
            )

            # Create indexes if needed
            if self.searchable:
                idx_name = f"ix_{table_name}_{self.name}"
                if self.field_type in [DynamicField.STRING, DynamicField.TEXT]:
                    db.session.execute(
                        text(
                            f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} USING gin ({self.name} gin_trgm_ops)"
                        )
                    )
                else:
                    db.session.execute(
                        text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({self.name})")
                    )

            # Update SQLAlchemy model
            column_type = self._column_types[self.field_type]
            if self.field_type == DynamicField.STRING and self.schema_config.get("max_length"):
                column_type = String(self.schema_config["max_length"])

            column_args = {"nullable": not self.required}
            setattr(model_class, self.name, Column(self.name, column_type, **column_args))

            logger.info(f"Successfully created column {self.name} in {table_name}")
            return True

        except Exception as e:
            logger.error(f"Error creating column {self.name}: {str(e)}")
            raise

    def drop_column(self):
        """Drop the column from entity table"""
        model_class = self.get_entity_model()
        table_name = model_class.__tablename__

        try:
            # Drop indexes first
            if self.searchable:
                idx_name = f"ix_{table_name}_{self.name}"
                db.session.execute(text(f"DROP INDEX IF EXISTS {idx_name}"))

            # Drop the column
            db.session.execute(text(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {self.name}"))
            db.session.commit()

            logger.info(f"Successfully dropped column {self.name} from {table_name}")
            return True

        except Exception as e:
            logger.error(f"Error dropping column {self.name}: {str(e)}")
            db.session.rollback()
            raise

    @classmethod
    def is_valid(cls, field_type: str) -> bool:
        """
        Check if a field type is valid

        Args:
            field_type: The field type to validate

        Returns:
            True if valid, False otherwise
        """
        return field_type in [
            cls.STRING,
            cls.INTEGER,
            cls.DATETIME,
            cls.ARRAY,
            cls.TEXT,
            cls.BOOLEAN,
            cls.FLOAT,
            cls.JSON,
        ]

    def validate_config(self):
        """Validate configuration based on field type"""
        if not self.schema_config:
            self.schema_config = {}

        # Validate based on field type
        if self.field_type == DynamicField.STRING:
            if "max_length" in self.schema_config:
                try:
                    max_length = int(self.schema_config["max_length"])
                    if max_length <= 0:
                        raise ValueError("max_length must be positive")
                except ValueError:
                    raise ValueError("max_length must be a valid integer")

    def get_entity_model(self):
        """Get the model class for this field's entity type"""
        from enferno.admin.models import Bulletin, Actor

        models = {"bulletin": Bulletin, "actor": Actor, "incident": Incident}

        if self.entity_type not in models:
            raise ValueError(f"Invalid entity type: {self.entity_type}")

        return models[self.entity_type]

    @classmethod
    def get_dynamic_columns(cls, entity_type):
        """Get all dynamic field definitions for a specific entity type"""
        return {
            field.name: field
            for field in cls.query.filter_by(entity_type=entity_type, active=True)
            .order_by(cls.sort_order)
            .all()
        }

    def to_dict(self):
        """Return dictionary representation of the field"""
        return {
            "id": self.id,
            "name": self.name,
            "title": self.title,
            "entity_type": self.entity_type,
            "field_type": self.field_type,
            "required": self.schema_config.get("required", self.required),
            "searchable": self.searchable,
            "config": self.config,
            "schema_config": self.schema_config,
            "ui_config": self.ui_config,
            "validation_config": self.validation_config,
            "options": self.options,
            "active": self.active,
        }
