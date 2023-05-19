from datetime import datetime
from flask_babel import gettext
from enferno.extensions import db
from enferno.utils.date_helper import DateHelper


class BaseMixin(object):
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted = db.Column(db.Boolean)

    def serialize_column(self, column_name):
        """
        generic serializer for all table columns (excluding relations etc .)
        :param column_name: name of db column
        :return: tuple : serialized representation or None with a True/False flag if operation is successful
        """
        columns = self.__table__.columns

        # for this custom class attribute, manually attach table name
        if column_name == 'class':
            return self.__table__.name

        elif column_name in columns:
            type_name = columns.get(column_name).type.__class__.__name__
            if type_name in ['String', 'Integer', 'ARRAY']:
                return getattr(self, column_name)
            elif type_name == 'DateTime':
                return DateHelper.serialize_datetime(getattr(self, column_name))

        # handle more complex types (relations etc ..)
        elif hasattr(self, column_name):
            cls = getattr(self, column_name)
            if hasattr(cls, 'to_dict') and callable(getattr(cls, 'to_dict')):
                return cls.to_dict()
            elif cls.__class__.__name__ == 'InstrumentedList':
                if column_name == f'{self.__tablename__}_relations':
                    return [item.to_dict(exclude=self) for item in cls]
                else:
                    return [item.to_dict() for item in cls]
        else:
            return f'---- needs implementation -----> {column_name}'

    def to_mini(self):
        output = {
            'id': self.id,
            'class': self.__tablename__
        }

        return output

    def min_json(self):
        at = ''
        if self.assigned_to:
            at = self.assigned_to.to_compact()
        fp = ''
        if self.first_peer_reviewer:
            fp = self.first_peer_reviewer.to_compact()
        output = {
            'id': self.id,
            'title': getattr(self, 'title', ''),
            'name': getattr(self, 'name', ''),
            'assigned_to': at,
            'first_peer_reviewer': fp,
            'status': self.status or '',
            "_status": gettext(self.status),
            "roles": [role.to_dict() for role in self.roles] if hasattr(self, 'roles') else '',

        }
        return output

    def restricted_json(self):
        return {
            'id': self.id,
            'restricted': True
        }

    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
            return self
        except Exception as e:
            print(str(e))
            db.session.rollback()
            return False

    def delete(self):
        try:
            db.session.delete(self)
            db.session.commit()
            return True
        except Exception as e:
            print(str(e))
            db.session.rollback()
            return False
