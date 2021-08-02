# -*- coding: utf-8 -*-
from flask_security import current_user
from sqlalchemy import JSON

from enferno.admin.models import Bulletin, Btob, Activity
from enferno.extensions import db
from enferno.utils.base import BaseMixin
import os
from enferno.settings import DevConfig, ProdConfig
CONFIG = ProdConfig if os.environ.get('FLASK_DEBUG') == '0' else DevConfig

# Deduplication relation
from enferno.user.models import User


class DedupRelation(db.Model, BaseMixin):
    """
    SQL Alchemy model for deduplication data, we store CSV data in this database model to process it later.
    """
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    query_video = db.Column(db.String, nullable=False)
    match_video = db.Column(db.String, nullable=False)
    distance = db.Column(db.Float, nullable=False)
    match_id = db.Column(db.String, unique=True, nullable=False)
    notes = db.Column(db.Text)
    status = db.Column(db.Integer, default=0)
    result = db.Column(JSON)

    STATUSES = {
        1: 'Relation already exists',
        2: 'Out of distance',
        3: 'Relationship added',
        4: 'Matching data not found'
    }

    def to_dict(self):
        return {
            'id': self.id,
            'query': self.query_video,
            'match': self.match_video,
            'distance': self.distance,
            'match_id': self.match_id,
            'status': self.status,
            'hstatus': self.STATUSES.get(self.status),
            'result': self.result
        }

    def process(self, user_id=1):
        """
        this method will go compare video deduplication data against database bulletins and establish relationship
        if it doesn't exist (based on the distance parameter provided by Benetech's video deduplication tool)
        :return: None
        """
        print("Processing match {}: {},{}".format(self.id, self.query_video, self.match_video))

        if self.distance > CONFIG.DEDUP_MAX_DISTANCE:
            self.status = 2
        elif self.query_video != self.match_video:
            b1 = Bulletin.query.filter_by(originid=self.query_video).first()
            b2 = Bulletin.query.filter_by(originid=self.match_video).first()
            if b1 and b2:
                rel_ids = sorted((b1.id, b2.id))
                relation = Btob.query.get(rel_ids)
                if relation:
                    self.status = 1
                else:
                    b = Btob(bulletin_id=rel_ids[0], related_bulletin_id=rel_ids[1])
                    if self.distance < CONFIG.DEDUP_LOW_DISTANCE:
                        b.related_as = 5
                        self.notes = "Potentially Duplicate"

                    if self.distance >= CONFIG.DEDUP_LOW_DISTANCE and self.distance <= CONFIG.DEDUP_MAX_DISTANCE:
                        b.related_as = 6
                        self.notes = "Potentially Related"
                    b.comment = '{}'.format(self.distance)

                    b.save()
                    revision_comment = 'Btob (type {}) created from match {}-{} distance {}'.format(b.related_as,
                                                                                                    rel_ids[0],
                                                                                                    rel_ids[1],
                                                                                                    self.distance)

                    b1.comments = revision_comment
                    b2.comments = revision_comment

                    # Save Bulletins and register activities
                    b1.create_revision()
                    user = User.query.get(user_id)
                    Activity.create(user, Activity.ACTION_UPDATE, b1.to_mini(), 'bulletin')
                    b2.create_revision()
                    Activity.create(user, Activity.ACTION_UPDATE, b2.to_mini(), 'bulletin')

                    relation_dict = {'class': 'btob', 'b1': '{}'.format(b.bulletin_id),
                                     'b2': '{}'.format(b.related_bulletin_id), 'type': '{}'.format(b.related_as)}

                    self.status = 3
                    self.result = relation_dict

            else:
                self.status = 4
        self.save()
        print("Completed match {}".format(self.id))
