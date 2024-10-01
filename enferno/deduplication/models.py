# -*- coding: utf-8 -*-

import time
from sqlalchemy import JSON

from enferno.admin.models import Bulletin, Btob, Activity, Media
from enferno.extensions import db, rds
from enferno.utils.base import BaseMixin
import os
from enferno.settings import Config as CONFIG


# Deduplication relation
from enferno.user.models import User
from enferno.utils.logging_utils import get_logger

logger = get_logger()


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
        1: "Relation already exists",
        2: "Out of distance",
        3: "Relationship added",
        4: "Matching data not found",
    }

    def to_dict(self) -> dict:
        """Return a dictionary representation of the object."""
        return {
            "id": self.id,
            "query": self.query_video,
            "match": self.match_video,
            "distance": self.distance,
            "match_id": self.match_id,
            "status": self.status,
            "hstatus": self.STATUSES.get(self.status),
            "result": self.result,
        }

    def lookup(self, video):
        return (
            Bulletin.query.filter_by(originid=video).first()
            or Bulletin.query.filter(Bulletin.medias.any(Media.search.ilike(f"%{video}%"))).first()
        )

    def process(self, user_id: int = 1) -> None:
        """
        this method will go compare video deduplication data against database bulletins and establish relationship
        if it doesn't exist (based on the distance parameter provided by Benetech's video deduplication tool)

        Args:
            - user_id: The id of the user who is processing the match

        Returns:
            None
        """

        logger.info(
            f"Match {self.id}: {self.query_video},{self.match_video}"
        )


        if self.distance > CONFIG.DEDUP_MAX_DISTANCE:
            self.status = 2
        elif self.query_video != self.match_video:
            b1 = self.lookup(self.query_video)
            b2 = self.lookup(self.match_video)

            if b1 and b2:
                while rds.sadd("dedup_processing", b1.id) == 0:
                    logger.info(f"Match {self.match_id} Bulletin {b1.id} is busy. Sleeping for 2...")
                    time.sleep(2)
                while rds.sadd("dedup_processing", b2.id) == 0:
                    logger.info(f"Match {self.match_id} Bulletin {b2.id} is busy. Sleeping for 2...")
                    time.sleep(2)

                logger.info(f"Processing match {self.match_id}...")

                existing_relation = Btob.are_related(b1.id, b2.id)

                if existing_relation:
                    self.status = 1
                else:
                    new_relation = Btob.relate(b1, b2)
                    if self.distance < CONFIG.DEDUP_LOW_DISTANCE:
                        new_relation.related_as = [6]
                        self.notes = "Potentially Duplicate"

                    if (
                        self.distance >= CONFIG.DEDUP_LOW_DISTANCE
                        and self.distance <= CONFIG.DEDUP_MAX_DISTANCE
                    ):
                        new_relation.related_as = [7]
                        self.notes = "Potentially Related"
                    new_relation.comment = f"{self.distance}"

                    new_relation.save()
                    revision_comment = f"Btob (type {self.notes}) created from match {self.query_video}-{self.match_video} distance {self.distance}"

                    b1.comments = revision_comment
                    b2.comments = revision_comment

                    # Save Bulletins and register activities
                    b1.create_revision()
                    user = User.query.get(user_id)
                    Activity.create(
                        user,
                        Activity.ACTION_UPDATE,
                        Activity.STATUS_SUCCESS,
                        b1.to_mini(),
                        "bulletin",
                    )
                    b2.create_revision()
                    Activity.create(
                        user,
                        Activity.ACTION_UPDATE,
                        Activity.STATUS_SUCCESS,
                        b2.to_mini(),
                        "bulletin",
                    )

                    relation_dict = {
                        "class": "btob",
                        "b1": "{}".format(new_relation.bulletin_id),
                        "b2": "{}".format(new_relation.related_bulletin_id),
                        "type": "{}".format(new_relation.related_as),
                    }

                    self.status = 3
                    self.result = relation_dict

                x = rds.srem("dedup_processing", b1.id)
                y = rds.srem("dedup_processing", b2.id)
                logger.info(f"Processed match {self.match_id} {x} {y}")

            else:
                self.status = 4
        self.save()
        logger.info(f"Completed match {self.match_id}")

