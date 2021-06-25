# -*- coding: utf-8 -*-
from enferno.extensions import db
from enferno.utils.base import BaseMixin
from sqlalchemy import JSON
from enferno.admin.models import Bulletin, Btob, Activity
from flask_security import current_user

# Deduplication relation
class DedupRelation(db.Model, BaseMixin):
    """
    SQL Alchemy model for deduplication data, we store CSV data in this database model to process it later.
    """
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    query_video = db.Column(db.String, nullable=False)
    match_video = db.Column(db.String, nullable=False)
    distance = db.Column(db.Float,nullable=False)
    notes = db.Column(db.Text)
    status = db.Column(db.Integer, default=0)
    result = db.Column(JSON)

    STATUSES = {
        1: 'Relation already exists',
        2: 'Distance > 0.5',
        3: 'Relationship added',
        4: 'Matching data not found'
    }


    def to_dict(self):
        return {
            'id': self.id,
            'query': self.query_video,
            'match': self.match_video,
            'distance': self.distance,
            'status': self.status,
            'hstatus': self.STATUSES.get(self.status),
            'result': self.result
        }




    def process(self):
        """
        this method will go compare video deduplication data against database bulletins and establish relationship
        if it doesn't exist (based on the distance parameter provided by Benetech's video deduplication tool)
        :return: None
        """
        b1 = Bulletin.query.filter_by(originid=self.query_video).first()
        b2 = Bulletin.query.filter_by(originid=self.match_video).first()
        if b1 and b2:
            rel_ids = sorted((b1.id,b2.id))
            relation = Btob.query.get(rel_ids)
            if relation:
                self.status = 1
            else:
                if self.distance > 0.5:
                    self.status = 2
                    return

                b = Btob(bulletin_id=rel_ids[0], related_bulletin_id=rel_ids[1])
                if self.distance < 0.3:
                    b.related_as = 5

                if self.distance >=0.3 and self.distance <=0.5:
                    b.related_as = 6
                b.comment = '{}'.format(self.distance)

                b.save()
                revision_comment = 'Btob (type {}) created from match {}-{} distance {}'.format(b.related_as, rel_ids[0], rel_ids[1], self.distance)

                b.bulletin_from.comments = revision_comment
                b.bulletin_to.comments = revision_comment
                b.bulletin_from.create_revision()

                # register activity
                Activity.create(current_user,Activity.ACTION_CREATE,b.bulletin_from.to_mini() ,'bulletin')
                b.bulletin_to.create_revision()
                Activity.create(current_user, Activity.ACTION_CREATE, b.bulletin_to.to_mini(), 'bulletin')

                relation_dict = {'class': 'btob', 'b1': '{}'.format(b.bulletin_id),'b2': '{}'.format(b.related_bulletin_id) }

                self.status = 3
                self.result = relation_dict

        else:
            self.status = 4


