# -*- coding: utf-8 -*-
import os
from collections import namedtuple

from celery import Celery

from enferno.admin.models import Bulletin, Actor, Incident, BulletinHistory, Activity, ActorHistory, IncidentHistory
from enferno.extensions import db
from enferno.settings import ProdConfig, DevConfig
from enferno.user.models import Role
from enferno.utils.data_import import DataImport

# Load configuraitons based on environment settings
if os.getenv("FLASK_DEBUG") == '0':
    cfg = ProdConfig
else:
    cfg = DevConfig

celery = Celery('tasks', broker=cfg.CELERY_BROKER_URL)
# remove deprecated warning
celery.conf.update(
    {'CELERY_ACCEPT_CONTENT': ['pickle', 'json', 'msgpack', 'yaml']})
celery.conf.update({'CELERY_RESULT_BACKEND': cfg.CELERY_RESULT_BACKEND})
celery.conf.add_defaults(cfg)


# Class to run tasks within application's context
class ContextTask(celery.Task):
    abstract = True
    def __call__(self, *args, **kwargs):
        from enferno.app import create_app
        from dotenv import load_dotenv
        load_dotenv()
        # Fixes
        cfg.SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
        with create_app(cfg).app_context():
            return super(ContextTask, self).__call__(*args, **kwargs)


celery.Task = ContextTask


def generate_system_roles():
    # create admin role if it doesn't exist
    r = Role.query.filter_by(name='Admin').first()
    if not r:
        Role(name='Admin').save()

    # create DA role, if not exists
    r = Role.query.filter_by(name='DA').first()
    if not r:
        Role(name='DA').save()

    # create MOD role, if not exists
    r = Role.query.filter_by(name='Mod').first()
    if not r:
        Role(name='Mod').save()


@celery.task
def bulk_update_bulletins(ids, bulk, cur_user_id):
    # build mappings
    u = {'id': cur_user_id}
    cur_user = namedtuple('cur_user', u.keys())(*u.values())
    mappings = []
    for bid in ids:
        tmp = bulk.copy()
        tmp['id'] = bid
        # indicate a bulk operation in the log
        tmp['comments'] = tmp.get('comments', '') + '*'

        # ----- handle refs update without losing existing values -------
        # grab existing refs (list)
        refs = Bulletin.query.with_entities(Bulletin.ref).filter_by(id=bid).first().ref
        if not refs:
            refs = []
        replace = tmp.get('refReplace')
        if replace:
            tmp['ref'] = tmp.get('ref', [])

        else:
            # append to existing refs
            tmp['ref'] = refs + tmp.get('ref', [])

        # handle automatic status assignement
        if not 'status' in tmp:
            if tmp.get('assigned_to_id'):
                status = 'Assigned'
            if tmp.get('first_peer_reviewer_id'):
                status = 'Peer Review Assigned'
            tmp['status'] = status

        mappings.append(tmp)

    db.session.bulk_update_mappings(Bulletin, mappings)

    revmaps = []
    bulletins = Bulletin.query.filter(Bulletin.id.in_(ids)).all()
    for bulletin in bulletins:
        # this commits automatically
        tmp = {
            'bulletin_id': bulletin.id,
            'user_id': cur_user.id,
            'data': bulletin.to_dict()
        }
        revmaps.append(tmp)
    db.session.bulk_insert_mappings(BulletinHistory, revmaps)

    # Record Activity
    updated = [b.to_mini() for b in bulletins]
    Activity.create(cur_user, Activity.ACTION_BULK_UPDATE, updated, 'bulletin')
    print("Bulletins Bulk Update Successful")


@celery.task
def bulk_update_actors(ids, bulk, cur_user_id):
    # build mappings
    u = {'id': cur_user_id}
    cur_user = namedtuple('cur_user', u.keys())(*u.values())
    mappings = []
    for bid in ids:
        tmp = bulk.copy()
        tmp['id'] = bid
        # indicate a bulk operation in the log
        tmp['comments'] = tmp.get('comments', '') + '*'

        # handle automatic status assignement
        if not 'status' in tmp:
            if tmp.get('assigned_to_id'):
                status = 'Assigned'
            if tmp.get('first_peer_reviewer_id'):
                status = 'Peer Review Assigned'
            tmp['status'] = status
        mappings.append(tmp)
    db.session.bulk_update_mappings(Actor, mappings)

    revmaps = []
    actors = Actor.query.filter(Actor.id.in_(ids)).all()
    for actor in actors:
        # this commits automatically
        tmp = {
            'actor_id': actor.id,
            'user_id': cur_user.id,
            'data': actor.to_dict()
        }
        revmaps.append(tmp)
    db.session.bulk_insert_mappings(ActorHistory, revmaps)

    # Record Activity
    updated = [a.to_mini() for a in actors]
    Activity.create(cur_user, Activity.ACTION_BULK_UPDATE, updated, 'actor')
    print("Actors Bulk Update Successful")


@celery.task
def bulk_update_incidents(ids, bulk, cur_user_id):
    # build mappings
    u = {'id': cur_user_id}
    cur_user = namedtuple('cur_user', u.keys())(*u.values())
    mappings = []
    for bid in ids:
        tmp = bulk.copy()
        tmp['id'] = bid
        # indicate a bulk operation in the log
        tmp['comments'] = tmp.get('comments', '') + '*'

        # handle automatic status assignement
        if not 'status' in tmp:
            if tmp.get('assigned_to_id'):
                status = 'Assigned'
            if tmp.get('first_peer_reviewer_id'):
                status = 'Peer Review Assigned'
            tmp['status'] = status

        mappings.append(tmp)
    db.session.bulk_update_mappings(Incident, mappings)

    revmaps = []
    incidents = Incident.query.filter(Incident.id.in_(ids)).all()
    for incident in incidents:
        # this commits automatically
        tmp = {
            'incident_id': incident.id,
            'user_id': cur_user.id,
            'data': incident.to_dict()
        }
        revmaps.append(tmp)
    db.session.bulk_insert_mappings(IncidentHistory, revmaps)

    # Record Activity
    updated = [i.to_mini() for i in incidents]
    Activity.create(cur_user, Activity.ACTION_BULK_UPDATE, updated, 'incident')
    print("Incidents Bulk Update Successful")


@celery.task(rate_limit=10)
def etl_process_file(batch_id, file, meta, user_id, log):
    di = DataImport(batch_id, meta, user_id=user_id, log=log)
    di.process(file)
    return 'done'
