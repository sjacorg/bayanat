# -*- coding: utf-8 -*-
import os
from collections import namedtuple

from celery import Celery


from enferno.admin.models import Bulletin, Actor, Incident, BulletinHistory, Activity, ActorHistory, IncidentHistory, Label, Eventtype, PotentialViolation, ClaimedViolation
from enferno.extensions import db, rds
from enferno.settings import ProdConfig, DevConfig
from enferno.user.models import Role
from enferno.utils.data_import import DataImport
from enferno.deduplication.models import DedupRelation
from datetime import timedelta
from enferno.utils.sheet_utils import SheetUtils


cfg = ProdConfig if os.environ.get('FLASK_DEBUG') == '0' else DevConfig



celery = Celery('tasks', broker=cfg.celery_broker_url)
# remove deprecated warning
celery.conf.update(
    {'accept_content': ['pickle', 'json', 'msgpack', 'yaml']})
celery.conf.update({'result_backend': os.environ.get('RESULT_BACKEND', cfg.result_backend)})
celery.conf.update({'SQLALCHEMY_DATABASE_URI': os.environ.get('SQLALCHEMY_DATABASE_URI', cfg.SQLALCHEMY_DATABASE_URI)})
celery.conf.update({'SECRET_KEY': os.environ.get('SECRET_KEY', cfg.SECRET_KEY)})
celery.conf.add_defaults(cfg)


# Class to run tasks within application's context
class ContextTask(celery.Task):
    abstract = True
    def __call__(self, *args, **kwargs):
        from enferno.app import create_app
        with create_app(cfg).app_context():
            return super(ContextTask, self).__call__(*args, **kwargs)


celery.Task = ContextTask


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


# this will publish a message to redis and will be captured by the front-end client
def update_stats():
    # send any message to refresh the UI
    # this will run only if the process is on
    rds.publish('dedprocess', 1)


@celery.task
def process_dedup(id, user_id):
    #print('processing {}'.format(id))
    d = DedupRelation.query.get(id)
    if d:
        d.process(user_id)
        # detect final task and send a refresh message
        if rds.scard('dedq') == 0:
            rds.publish('dedprocess', 2)


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    seconds = int(os.environ.get('DEDUP_INTERVAL', cfg.DEDUP_INTERVAL))
    sender.add_periodic_task(seconds, dedup_cron.s(), name='Deduplication Cron')


# @periodic_task(run_every=timedelta(seconds=int(os.environ.get('DEDUP_INTERVAL', cfg.DEDUP_INTERVAL))))
@celery.task
def dedup_cron():
    if cfg.DEDUP_TOOL == True:
        #shut down processing when we hit 0 items in the queue or when we turn off the processing
        if rds.get('dedup') != '1' or rds.scard('dedq') == 0:
            rds.delete('dedup')
            rds.publish('dedprocess', 0)
            # Pause processing / do nothing
            print("Process engine - off")
            return

        data = []
        items = rds.spop('dedq', cfg.DEDUP_BATCH_SIZE)
        for item in items:
            data = item.split('|')
            process_dedup.delay(data[0], data[1])

        update_stats()


@celery.task
def process_sheet(filepath, map, target, batch_id,vmap, sheet, actorConfig):
    su = SheetUtils(filepath, actorConfig)
    su.import_sheet(map, target, batch_id, vmap, sheet)


def generate_user_roles():
    '''
    Generates standard user roles.
    '''
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


def import_data():
    '''
    Imports SJAC data from data dir.
    '''
    data_path = 'enferno/data/'
    from werkzeug.datastructures import FileStorage

    # Eventtypes
    if not Eventtype.query.count():
        f = data_path + 'eventtypes.csv'
        fs = FileStorage(open(f, 'rb'))
        Eventtype.import_csv(fs)

    # potential violations
    if not PotentialViolation.query.count():
        f = data_path + 'potential_violation.csv'
        fs = FileStorage(open(f, 'rb'))
        PotentialViolation.import_csv(fs)

    # claimed violations
    if not ClaimedViolation.query.count():
        f = data_path + 'claimed_violation.csv'
        fs = FileStorage(open(f, 'rb'))
        ClaimedViolation.import_csv(fs)
