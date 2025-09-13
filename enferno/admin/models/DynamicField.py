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
    Table,
    MetaData,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import text
from enferno.admin.models import Incident
from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.logging_utils import get_logger
from enferno.utils.date_helper import DateHelper

logger = get_logger()


class DynamicField(db.Model, BaseMixin):
    """
    Defines dynamic custom fields for any entity type (bulletin, actor, incident).

    Supports 6 clean field types:
    - TEXT: Short text input (varchar 255)
    - LONG_TEXT: Long text area
    - NUMBER: Numeric input (integer)
    - SINGLE_SELECT: Dropdown selection
    - MULTI_SELECT: Multi-select dropdown (stored as array)
    - DATETIME: Date and time picker

    JSONB Field Documentation:

    - schema_config (JSONB): Database-related config.
        Example:
        {
            "required": true,
            "default": "",
            "max_length": 100
        }

    - ui_config (JSONB): UI rendering config.
        Example:
        {
            "help_text": "Enter your full legal name.",
            "width": "w-100"
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
            {"label": "Administrator", "value": "admin"},
            {"label": "User", "value": "user"}
        ]
    """

    __tablename__ = "dynamic_fields"

    # Data Types (clean separation from UI components)
    TEXT = "text"  # Short text input
    LONG_TEXT = "long_text"  # Long text area
    NUMBER = "number"  # Numeric input
    SINGLE_SELECT = "single_select"  # Single choice dropdown
    MULTI_SELECT = "multi_select"  # Multiple choice selection
    DATETIME = "datetime"  # Date and time picker
    HTML_BLOCK = "html_block"  # Existing HTML component/template (for complex core fields)

    # UI Components for rendering (clean, lean set)
    class UIComponent:
        INPUT = "input"
        TEXTAREA = "textarea"
        NUMBER_INPUT = "number_input"
        DATE_PICKER = "date_picker"
        DROPDOWN = "dropdown"
        MULTI_DROPDOWN = "multi_dropdown"
        HTML_BLOCK = "html_block"  # Renders existing HTML template/component

    # Data type to UI component mapping (1:1, extensible)
    COMPONENT_MAP = {
        TEXT: [UIComponent.INPUT],
        LONG_TEXT: [UIComponent.TEXTAREA],
        NUMBER: [UIComponent.NUMBER_INPUT],
        SINGLE_SELECT: [UIComponent.DROPDOWN],
        MULTI_SELECT: [UIComponent.MULTI_DROPDOWN],
        DATETIME: [UIComponent.DATE_PICKER],
        HTML_BLOCK: [UIComponent.HTML_BLOCK],  # Maps to existing HTML template
    }

    # Clean field type to SQL type mapping
    TYPE_MAP = {
        TEXT: "varchar(255)",  # Short text input
        LONG_TEXT: "text",  # Long text area
        NUMBER: "integer",  # Numeric input
        SINGLE_SELECT: "varchar(255)[]",  # Single choice (stores array with ≤1 element)
        MULTI_SELECT: "varchar(255)[]",  # Multiple choice (stores array of values)
        DATETIME: "timestamp with time zone",  # Date and time
    }

    # SQLAlchemy column types for clean data type mapping
    _column_types = {
        TEXT: String(255),  # Short text input
        LONG_TEXT: Text,  # Long text area
        NUMBER: Integer,  # Numeric input
        SINGLE_SELECT: SQLArray(String(255)),  # Single choice (array with ≤1 element)
        MULTI_SELECT: SQLArray(String(255)),  # Multiple choice selection
        DATETIME: DateTime(timezone=True),  # Date and time
    }

    id = db.Column(db.Integer, primary_key=True)  # Primary key
    name = db.Column(db.String(50), nullable=False)  # Python identifier for the field
    title = db.Column(db.String(100), nullable=False)  # Human-readable label
    entity_type = db.Column(
        db.String(50), nullable=False
    )  # Target entity/table (e.g., 'bulletin', 'actor')
    field_type = db.Column(
        db.String(20), nullable=False
    )  # Data type (text, number, single_select, etc.)

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
    sort_order = db.Column(db.Integer, default=0)  # Field display order within entity
    core = db.Column(db.Boolean, default=False)  # Whether this is a core (built-in) field

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

        # Check reserved names only for new non-core fields
        if not self.id and not self.core:  # Skip validation for core fields
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

        # Validate options if select fields (skip for core fields)
        if (
            self.field_type in [self.SINGLE_SELECT, self.MULTI_SELECT]
            and not self.options
            and not self.core  # Skip validation for core fields
        ):
            raise ValueError(f"Options are required for {self.field_type} fields")

        # Validate config based on field type
        self.validate_config()

    def ensure_option_ids(self):
        """Ensure all options have unique incremental IDs - never reassign existing ones"""
        if not self.options or not isinstance(self.options, list):
            return

        # Find highest existing ID
        existing_ids = [opt.get("id", 0) for opt in self.options if isinstance(opt, dict)]
        max_id = max(existing_ids) if existing_ids else 0

        # Only assign IDs to options that don't have one
        for option in self.options:
            if isinstance(option, dict) and not option.get("id"):
                max_id += 1
                option["id"] = max_id

    def save(self):
        """Save the field after validating if not already validated"""
        if not getattr(self, "_validated", False):
            self.validate_field()
            self._validated = True

        # Ensure options have IDs for select fields
        if self.field_type in [self.SINGLE_SELECT, self.MULTI_SELECT]:
            self.ensure_option_ids()

        return super().save()

    def create_column(self):
        """Create the actual column in the entity table"""
        model_class = self.get_entity_model()
        table_name = model_class.__tablename__

        try:
            # Direct mapping from field_type to SQL type
            sql_type = DynamicField.TYPE_MAP.get(self.field_type)
            if not sql_type:
                raise ValueError(f"Invalid field type: {self.field_type}")

            constraints = []
            if self.schema_config.get("required", False):
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
                if self.field_type in [DynamicField.SINGLE_SELECT, DynamicField.MULTI_SELECT]:
                    # Use GIN index for array columns (both single and multi-select)
                    db.session.execute(
                        text(
                            f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} USING gin ({self.name})"
                        )
                    )
                elif self.field_type in [DynamicField.TEXT, DynamicField.LONG_TEXT]:
                    # Use GIN trigram index for text search
                    db.session.execute(
                        text(
                            f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} USING gin ({self.name} gin_trgm_ops)"
                        )
                    )
                else:
                    # Standard B-tree index for numbers, datetime
                    db.session.execute(
                        text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({self.name})")
                    )

            # Update SQLAlchemy model - direct mapping from field_type
            column_type = self._column_types.get(self.field_type)
            if self.field_type == DynamicField.TEXT and self.schema_config.get("max_length"):
                column_type = String(self.schema_config["max_length"])

            column_args = {"nullable": not self.schema_config.get("required", False)}
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
            cls.TEXT,  # Short text input
            cls.LONG_TEXT,  # Long text area
            cls.NUMBER,  # Numeric input
            cls.SINGLE_SELECT,  # Single choice dropdown
            cls.MULTI_SELECT,  # Multiple choice selection
            cls.DATETIME,  # Date and time
            cls.HTML_BLOCK,  # Existing HTML template/component
        ]

    def validate_config(self):
        """Validate configuration based on field type"""
        if not self.schema_config:
            self.schema_config = {}

        # Validate based on field type
        if self.field_type == DynamicField.TEXT:
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

    @staticmethod
    def _serialize_value(field_type: str, value):
        """Serialize a dynamic field value based on its type."""
        if value is None:
            if field_type == DynamicField.MULTI_SELECT:
                return []
            return ""

        if field_type == DynamicField.DATETIME:
            return DateHelper.serialize_datetime(value)

        if field_type == DynamicField.MULTI_SELECT:
            # Stored as a native array (e.g., varchar[]). Return as-is (or empty list).
            return list(value) if value is not None else []

        return value

    @classmethod
    def extract_values_for(cls, entity) -> dict:
        """Extract current values for all active non-core dynamic fields on an entity.

        Returns a flat dict {field_name: serialized_value} suitable for merging
        into the entity's to_dict output.
        """
        # Infer entity_type from table name (e.g., Bulletin -> "bulletin")
        entity_type = getattr(entity, "__tablename__", None)
        if not entity_type:
            return {}

        values = {}

        fields = (
            cls.query.filter(
                cls.entity_type == entity_type,
                cls.active.is_(True),
                cls.core.is_(False),  # Exclude core fields - they're handled by model's to_dict
            )
            .order_by(cls.sort_order)
            .all()
        )

        if not fields:
            return values

        # Use SQLAlchemy Core to read current values from DB
        try:
            meta = MetaData()
            table = Table(entity_type, meta, autoload_with=db.engine)

            # Build select for existing columns only
            field_names = [f.name for f in fields if f.name in table.columns]
            if not field_names:
                return values

            # Select current values
            stmt = table.select().where(table.c.id == entity.id)
            result = db.session.execute(stmt).first()

            if result:
                for field in fields:
                    if field.name in table.columns:
                        raw = getattr(result, field.name, None)
                        values[field.name] = cls._serialize_value(field.field_type, raw)

        except Exception as e:
            logger.error(
                f"Failed to extract dynamic field values for {entity_type}#{entity.id}: {e}",
                exc_info=True,
            )

        return values

    @classmethod
    def apply_values(cls, entity, data: dict) -> None:
        """Apply incoming dynamic field values via SQLAlchemy Core (reliable, no ORM mapping needed).

        - Uses fresh table metadata from DB to check column existence
        - Coerces values by field type before update
        - Updates via Core SQL, no setattr needed
        """
        entity_type = getattr(entity, "__tablename__", None)
        if not entity_type or not isinstance(data, dict):
            return

        # Get active non-core dynamic fields
        fields = (
            cls.query.filter(
                cls.entity_type == entity_type,
                cls.active.is_(True),
                cls.core.is_(False),  # Exclude core fields - they're handled by model's from_json
            )
            .order_by(cls.sort_order)
            .all()
        )

        # Build coerced updates dict
        updates = {}
        for field in fields:
            name = field.name
            if name not in data:
                continue
            value = data.get(name)

            # Coerce value by field type
            if value is None:
                updates[name] = None
            elif field.field_type == cls.DATETIME:
                updates[name] = DateHelper.parse_datetime(value)
            elif field.field_type == cls.MULTI_SELECT:
                updates[name] = list(value) if isinstance(value, (list, tuple)) else [value]
            elif field.field_type == cls.NUMBER:
                try:
                    updates[name] = int(value) if value is not None else None
                except (TypeError, ValueError):
                    updates[name] = None
            else:
                updates[name] = value

        if not updates:
            return

        # Use SQLAlchemy Core with fresh table metadata
        try:
            meta = MetaData()
            table = Table(entity_type, meta, autoload_with=db.engine)

            # Filter to only existing columns
            safe_updates = {k: v for k, v in updates.items() if k in table.columns}

            if safe_updates:
                stmt = update(table).where(table.c.id == entity.id).values(safe_updates)
                db.session.execute(stmt)

        except Exception as e:
            logger.error(
                f"Failed to apply dynamic fields via Core on {entity_type}#{entity.id}: {e}",
                exc_info=True,
            )

    def to_dict(self):
        """Return dictionary representation of the field"""
        return {
            "id": self.id,
            "name": self.name,
            "title": self.title,
            "entity_type": self.entity_type,
            "field_type": self.field_type,
            "ui_component": self.ui_component,
            "required": self.schema_config.get("required", False),
            "searchable": self.searchable,
            "schema_config": self.schema_config,
            "ui_config": self.ui_config,
            "validation_config": self.validation_config,
            "options": self.options,
            "active": self.active,
            "sort_order": self.sort_order,
            "core": self.core,
        }
