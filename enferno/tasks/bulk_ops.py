# -*- coding: utf-8 -*-
import time
from collections import namedtuple

import enferno.utils.typing as t
from enferno.admin.constants import Constants
from enferno.admin.models import (
    Activity,
    Actor,
    ActorHistory,
    Bulletin,
    BulletinHistory,
    Incident,
    IncidentHistory,
)
from enferno.admin.models.Notification import Notification
from enferno.extensions import db
from enferno.tasks import BULK_CHUNK_SIZE, celery, chunk_list
from enferno.user.models import Role, User
from enferno.utils.logging_utils import get_logger

logger = get_logger("celery.tasks.bulk_ops")


@celery.task
def bulk_update_bulletins(ids: list, bulk: dict, cur_user_id: t.id) -> None:
    """
    Bulk update bulletins task.

    Args:
        - ids: List of bulletin ids to update.
        - bulk: Bulk update data.
        - cur_user_id: ID of the user performing the bulk update.

    Returns:
        None
    """
    logger.info(f"Processing Bulletin bulk-update... User ID: {cur_user_id} Total: {len(ids)}")
    # build mappings
    u = {"id": cur_user_id}
    cur_user = namedtuple("cur_user", u.keys())(*u.values())
    user = User.query.get(cur_user_id)
    chunks = chunk_list(ids, BULK_CHUNK_SIZE)

    # Assigned user
    assigned_to_id = bulk.get("assigned_to_id")
    clear_assignee = bulk.get("assigneeClear")

    # FPR user
    first_peer_reviewer_id = bulk.get("first_peer_reviewer_id")
    clear_reviewer = bulk.get("reviewerClear")

    for group in chunks:
        # Fetch bulletins
        bulletins = Bulletin.query.filter(Bulletin.id.in_(group))
        for bulletin in bulletins:
            # check user can access each bulletin
            if not user.can_access(bulletin):
                # Log?
                continue

            # get Status initially
            status = bulk.get("status")

            if clear_assignee:
                bulletin.assigned_to_id = None
            elif assigned_to_id:
                bulletin.assigned_to_id = assigned_to_id
                if not status:
                    bulletin.status = "Assigned"

            if clear_reviewer:
                bulletin.first_peer_reviewer_id = None
            elif first_peer_reviewer_id:
                bulletin.first_peer_reviewer_id = first_peer_reviewer_id
                if not status:
                    bulletin.status = "Peer Review Assigned"

            if status:
                bulletin.status = status

            # Ref
            tags = bulk.get("tags")
            if tags:
                if bulk.get("tagsReplace") or not bulletin.tags:
                    bulletin.tags = tags
                else:
                    # merge refs / remove dups
                    bulletin.tags = list(set(bulletin.tags + tags))

            # Comment (required)
            bulletin.comments = bulk.get("comments", "")

            # Access Roles
            roles = bulk.get("roles")
            replace_roles = bulk.get("rolesReplace")
            if replace_roles:
                if roles:
                    role_ids = list(map(lambda x: x.get("id"), roles))
                    # get actual roles objects
                    roles = Role.query.filter(Role.id.in_(role_ids)).all()
                    # assign directly to the bulletin
                    bulletin.roles = roles
                else:
                    # clear bulletin roles
                    bulletin.roles = []
            else:
                if roles:
                    # merge roles
                    role_ids = list(map(lambda x: x.get("id"), roles))
                    # get actual roles objects
                    roles = Role.query.filter(Role.id.in_(role_ids)).all()
                    # assign directly to the bulletin
                    bulletin.roles = list(set(bulletin.roles + roles))

            # add only to session
            db.session.add(bulletin)

        revmaps = []
        bulletins = Bulletin.query.filter(Bulletin.id.in_(group)).all()
        for bulletin in bulletins:
            # this commits automatically
            tmp = {"bulletin_id": bulletin.id, "user_id": cur_user.id, "data": bulletin.to_dict()}
            revmaps.append(tmp)
        db.session.bulk_insert_mappings(BulletinHistory, revmaps)

        # commit session when a batch of items and revisions are added
        db.session.commit()

        # Record Activity
        updated = [b.to_mini() for b in bulletins]
        Activity.create(
            cur_user, Activity.ACTION_BULK_UPDATE, Activity.STATUS_SUCCESS, updated, "bulletin"
        )
        # perhaps allow a little time out
        time.sleep(0.1)

    logger.info(f"Bulletin bulk-update successful. User ID: {cur_user_id} Total: {len(ids)}")

    assigner = User.query.get(cur_user_id)
    # Notify admin
    Notification.send_notification_for_event(
        Constants.NotificationEvent.BULK_OPERATION_STATUS,
        assigner,
        "Bulk Operation Status",
        f"Bulk update of {len(ids)} Bulletins has been completed successfully.",
    )

    # send notifications for assignments and reviews
    if assigned_to_id:
        Notification.send_notification_for_event(
            Constants.NotificationEvent.NEW_ASSIGNMENT,
            User.query.get(assigned_to_id),
            "New Assignment",
            f"{len(ids)} Bulletins have been assigned to you by {assigner.username} for analysis.",
        )

    if first_peer_reviewer_id:
        Notification.send_notification_for_event(
            Constants.NotificationEvent.REVIEW_NEEDED,
            User.query.get(first_peer_reviewer_id),
            "Review Needed",
            f"{len(ids)} Bulletins have been assigned to you by {assigner.username} for review.",
        )


@celery.task
def bulk_update_actors(ids: list, bulk: dict, cur_user_id: t.id) -> None:
    """
    Bulk update actors task.

    Args:
        - ids: List of actor ids to update.
        - bulk: Bulk update data.
        - cur_user_id: ID of the user performing the bulk update.

    Returns:
        None
    """
    logger.info(f"Processing Actor bulk-update... User ID: {cur_user_id} Total: {len(ids)}")
    # build mappings
    u = {"id": cur_user_id}
    cur_user = namedtuple("cur_user", u.keys())(*u.values())
    user = User.query.get(cur_user_id)
    chunks = chunk_list(ids, BULK_CHUNK_SIZE)

    # Assigned user
    assigned_to_id = bulk.get("assigned_to_id")
    clear_assignee = bulk.get("assigneeClear")

    # FPR user
    first_peer_reviewer_id = bulk.get("first_peer_reviewer_id")
    clear_reviewer = bulk.get("reviewerClear")

    for group in chunks:
        # Fetch bulletins
        actors = Actor.query.filter(Actor.id.in_(group))
        for actor in actors:
            # check user can access each actor
            if not user.can_access(actor):
                # Log?
                continue

            # get Status initially
            status = bulk.get("status")

            if clear_assignee:
                actor.assigned_to_id = None
            elif assigned_to_id:
                actor.assigned_to_id = assigned_to_id
                if not status:
                    actor.status = "Assigned"

            if clear_reviewer:
                actor.first_peer_reviewer_id = None
            elif first_peer_reviewer_id:
                actor.first_peer_reviewer_id = first_peer_reviewer_id
                if not status:
                    actor.status = "Peer Review Assigned"

            if status:
                actor.status = status

            # Tags
            tags = bulk.get("tags")
            if tags:
                if bulk.get("tagsReplace") or not actor.tags:
                    actor.tags = tags
                else:
                    # merge tags / remove dups
                    actor.tags = list(set(actor.tags + tags))

            # Comment (required)
            actor.comments = bulk.get("comments", "")

            # Access Roles
            roles = bulk.get("roles")
            replace_roles = bulk.get("rolesReplace")
            if replace_roles:
                if roles:
                    role_ids = list(map(lambda x: x.get("id"), roles))
                    # get actual roles objects
                    roles = Role.query.filter(Role.id.in_(role_ids)).all()
                    # assign directly to the bulletin
                    actor.roles = roles
                else:
                    # clear actor roles
                    actor.roles = []
            else:
                if roles:
                    # merge roles
                    role_ids = list(map(lambda x: x.get("id"), roles))
                    # get actual roles objects
                    roles = Role.query.filter(Role.id.in_(role_ids)).all()
                    # assign directly to the actor
                    actor.roles = list(set(actor.roles + roles))

            # add only to session
            db.session.add(actor)

        revmaps = []
        actors = Actor.query.filter(Actor.id.in_(group)).all()
        for actor in actors:
            # this commits automatically
            tmp = {"actor_id": actor.id, "user_id": cur_user.id, "data": actor.to_dict()}
            revmaps.append(tmp)
        db.session.bulk_insert_mappings(ActorHistory, revmaps)

        # commit session when a batch of items and revisions are added
        db.session.commit()

        # Record Activity
        updated = [b.to_mini() for b in actors]
        Activity.create(
            cur_user, Activity.ACTION_BULK_UPDATE, Activity.STATUS_SUCCESS, updated, "actor"
        )
        # perhaps allow a little time out
        time.sleep(0.25)

    logger.info(f"Actors bulk-update successful. User ID: {cur_user_id} Total: {len(ids)}")

    assigner = User.query.get(cur_user_id)
    # Notify admin
    Notification.send_notification_for_event(
        Constants.NotificationEvent.BULK_OPERATION_STATUS,
        assigner,
        "Bulk Operation Status",
        f"Bulk update of {len(ids)} Actors has been completed successfully.",
    )

    # send notifications for assignments and reviews
    if assigned_to_id:
        Notification.send_notification_for_event(
            Constants.NotificationEvent.NEW_ASSIGNMENT,
            User.query.get(assigned_to_id),
            "New Assignment",
            f"{len(ids)} Actors have been assigned to you by {assigner.username} for analysis.",
        )

    if first_peer_reviewer_id:
        Notification.send_notification_for_event(
            Constants.NotificationEvent.REVIEW_NEEDED,
            User.query.get(first_peer_reviewer_id),
            "Review Needed",
            f"{len(ids)} Actors have been assigned to you by {assigner.username} for review.",
        )


@celery.task
def bulk_update_incidents(ids: list, bulk: dict, cur_user_id: t.id) -> None:
    """
    Bulk update incidents task.

    Args:
        - ids: List of incident ids to update.
        - bulk: Bulk update data.
        - cur_user_id: ID of the user performing the bulk update.

    Returns:
        None
    """
    logger.info(f"Processing Incident bulk-update... User ID: {cur_user_id} Total: {len(ids)}")
    # build mappings
    u = {"id": cur_user_id}
    cur_user = namedtuple("cur_user", u.keys())(*u.values())
    user = User.query.get(cur_user_id)
    chunks = chunk_list(ids, BULK_CHUNK_SIZE)

    # for ops on related items
    assign_related = bulk.get("assignRelated")
    restrict_related = bulk.get("restrictRelated")
    actors = []
    bulletins = []

    # Assigned user
    assigned_to_id = bulk.get("assigned_to_id")
    clear_assignee = bulk.get("assigneeClear")

    # FPR user
    first_peer_reviewer_id = bulk.get("first_peer_reviewer_id")
    clear_reviewer = bulk.get("reviewerClear")

    for group in chunks:
        # Fetch bulletins
        incidents = Incident.query.filter(Incident.id.in_(group))
        for incident in incidents:
            # check if user can access incident
            if not user.can_access(incident):
                # Log?
                continue

            # get Status initially
            status = bulk.get("status")

            if clear_assignee:
                incident.assigned_to_id = None
            elif assigned_to_id:
                incident.assigned_to_id = assigned_to_id
                if not status:
                    incident.status = "Assigned"

            if clear_reviewer:
                incident.first_peer_reviewer_id = None
            elif first_peer_reviewer_id:
                incident.first_peer_reviewer_id = first_peer_reviewer_id
                if not status:
                    incident.status = "Peer Review Assigned"

            if status:
                incident.status = status

            # Comment (required)
            incident.comments = bulk.get("comments", "")

            # Access Roles
            roles = bulk.get("roles")
            replace_roles = bulk.get("rolesReplace")
            if replace_roles:
                if roles:
                    role_ids = list(map(lambda x: x.get("id"), roles))
                    # get actual roles objects
                    roles = Role.query.filter(Role.id.in_(role_ids)).all()
                    # assign directly to the bulletin
                    incident.roles = roles
                else:
                    # clear incident roles
                    incident.roles = []
            else:
                if roles:
                    # merge roles
                    role_ids = list(map(lambda x: x.get("id"), roles))
                    # get actual roles objects
                    roles = Role.query.filter(Role.id.in_(role_ids)).all()
                    # assign directly to the incident
                    incident.roles = list(set(incident.roles + roles))

            if assign_related or restrict_related:
                rel_actors = [itoa.actor_id for itoa in incident.related_actors]
                actors.extend(rel_actors)

                rel_bulletins = [itoa.bulletin_id for itoa in incident.related_bulletins]
                bulletins.extend(rel_bulletins)

            # add only to session
            db.session.add(incident)

        revmaps = []
        incidents = Incident.query.filter(Incident.id.in_(group)).all()
        for incident in incidents:
            # this commits automatically
            tmp = {"incident_id": incident.id, "user_id": cur_user.id, "data": incident.to_dict()}
            revmaps.append(tmp)
        db.session.bulk_insert_mappings(IncidentHistory, revmaps)

        # commit session when a batch of items and revisions are added
        db.session.commit()

        # Record Activity
        updated = [b.to_mini() for b in incidents]
        Activity.create(
            cur_user, Activity.ACTION_BULK_UPDATE, Activity.STATUS_SUCCESS, updated, "incident"
        )

        # restrict or assign related items
        if assign_related or restrict_related:
            # remove status
            bulk.pop("status", None)

            # not assigning related items
            if not assign_related:
                bulk.pop("assigned_to_id", None)
                bulk.pop("first_peer_reviewer_id", None)

            # not restricting related items
            if not restrict_related:
                bulk.pop("roles", None)
                bulk.pop("rolesReplace", None)

            # carry out bulk ops on related items
            if len(actors):
                bulk_update_actors(actors, bulk, cur_user_id)
            if len(bulletins):
                bulk_update_bulletins(bulletins, bulk, cur_user_id)

        # perhaps allow a little time out
        time.sleep(0.25)

    logger.info(f"Incidents bulk-update successful. User ID: {cur_user_id} Total: {len(ids)}")

    assigner = User.query.get(cur_user_id)
    # Notify admin
    Notification.send_notification_for_event(
        Constants.NotificationEvent.BULK_OPERATION_STATUS,
        assigner,
        "Bulk Operation Status",
        f"Bulk update of {len(ids)} Incidents has been completed successfully.",
    )

    # send notifications for assignments and reviews
    if assigned_to_id:
        Notification.send_notification_for_event(
            Constants.NotificationEvent.NEW_ASSIGNMENT,
            User.query.get(assigned_to_id),
            "New Assignment",
            f"{len(ids)} Incidents have been assigned to you by {assigner.username} for analysis.",
        )

    if first_peer_reviewer_id:
        Notification.send_notification_for_event(
            Constants.NotificationEvent.REVIEW_NEEDED,
            User.query.get(first_peer_reviewer_id),
            "Review Needed",
            f"{len(ids)} Incidents have been assigned to you by {assigner.username} for review.",
        )
