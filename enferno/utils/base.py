from datetime import datetime
from flask_babel import gettext
from sqlalchemy.orm import declared_attr

from enferno.extensions import db
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger


logger = get_logger()


class DatabaseException(Exception):
    pass


class BaseMixin(object):
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted = db.Column(db.Boolean)

    def serialize_column(self, column_name):
        """
        generic serializer for all table columns (excluding relations etc .)
        :param column_name: name of db column
        :return: tuple : serialized representation or None with a True/False flag if operation is successful
        """
        # First try to get dynamic fields
        dynamic_fields = self.get_dynamic_fields()
        if column_name in dynamic_fields:
            return dynamic_fields[column_name]

        columns = self.__table__.columns

        # for this custom class attribute, manually attach table name
        if column_name == "class":
            return self.__table__.name

        elif column_name in columns:
            type_name = columns.get(column_name).type.__class__.__name__
            if type_name in ["String", "Integer", "ARRAY"]:
                return getattr(self, column_name)
            elif type_name == "DateTime":
                return DateHelper.serialize_datetime(getattr(self, column_name))

        # handle more complex types (relations etc ..)
        elif hasattr(self, column_name):
            cls = getattr(self, column_name)
            if hasattr(cls, "to_dict") and callable(getattr(cls, "to_dict")):
                return cls.to_dict()
            elif cls.__class__.__name__ == "InstrumentedList":
                if column_name == f"{self.__tablename__}_relations":
                    return [item.to_dict(exclude=self) for item in cls]
                else:
                    return [item.to_dict() for item in cls]
        else:
            return f"---- needs implementation -----> {column_name}"

    def get_dynamic_fields(self):
        from enferno.admin.models.DynamicField import DynamicField

        """Get all dynamic fields for this entity type - exclude core fields to avoid collisions with existing model attributes"""

        # Get the entity type from the table name
        entity_type = self.__tablename__.rstrip("s")  # Remove trailing 's' for plural

        # Query only NON-CORE dynamic fields to avoid collisions with existing model attributes
        dynamic_fields = DynamicField.query.filter_by(
            entity_type=entity_type, active=True, core=False
        ).all()

        return {field.name: getattr(self, field.name, None) for field in dynamic_fields}

    def serialize_relationship(self, relationship):
        return [rel.to_dict() for rel in relationship] if relationship else []

    def to_mini(self):
        output = {"id": self.id, "class": self.__tablename__}

        return output

    def min_json(self):
        at = ""
        if self.assigned_to:
            at = self.assigned_to.to_compact()
        fp = ""
        if self.first_peer_reviewer:
            fp = self.first_peer_reviewer.to_compact()
        output = {
            "id": self.id,
            "type": getattr(self, "type", None),
            "title": getattr(self, "title", ""),
            "name": getattr(self, "name", ""),
            "assigned_to": at,
            "first_peer_reviewer": fp,
            "status": self.status or "",
            "_status": gettext(self.status),
            "roles": [role.to_dict() for role in self.roles] if hasattr(self, "roles") else "",
        }
        return output

    def restricted_json(self):
        return {"id": self.id, "restricted": True}

    def save(self, raise_exception=False):
        try:
            db.session.add(self)
            db.session.commit()
            return self
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving {self.__class__.__name__}: {e}")
            # Backwards compatibility
            if raise_exception:
                raise DatabaseException(f"Error saving {self.__class__.__name__}: {e}")
            else:
                return False

    def delete(self, raise_exception=False):
        try:
            db.session.delete(self)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting {self.__class__.__name__}: {e}")
            # Backwards compatibility
            if raise_exception:
                raise DatabaseException(f"Error deleting {self.__class__.__name__}: {e}")
            else:
                return False

    def to_dict(self, mode=None):
        """Base implementation of to_dict that includes dynamic fields"""
        data = {}
        # Add dynamic fields only - system fields handled by child classes
        data.update(self.get_dynamic_fields())
        return data


class ComponentDataMixin(BaseMixin):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    title_tr = db.Column(db.String)

    def from_json(self, jsn):
        for key, value in jsn.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "title_tr": self.title_tr,
            "created_at": DateHelper.serialize_datetime(self.created_at),
            "updated_at": DateHelper.serialize_datetime(self.updated_at),
        }

    @classmethod
    def find_by_title(cls, title):
        item = cls.query.filter(cls.title_tr.ilike(title)).first()
        return item if item else cls.query.filter(cls.title.ilike(title)).first()
