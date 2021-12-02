from datetime import datetime
from flask_babelex import gettext
from enferno.extensions import db


class BaseMixin(object):
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted = db.Column(db.Boolean)

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
            'status': getattr(self, 'status', ''),
            "_status": gettext(self.status)

        }
        return output

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
        except Exception as e:
            print(str(e))
            db.session.rollback()
            return False
