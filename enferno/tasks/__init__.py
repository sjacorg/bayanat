# -*- coding: utf-8 -*-
import os, time
from collections import namedtuple
from celery import Celery
from enferno.admin.models import Bulletin, Actor, Incident, BulletinHistory, Activity, ActorHistory, IncidentHistory, \
    Label, Eventtype, PotentialViolation, ClaimedViolation, LocationAdminLevel, LocationType
from enferno.extensions import db, rds
from enferno.settings import ProdConfig, DevConfig
from enferno.user.models import Role, User
from enferno.utils.data_import import DataImport
from enferno.deduplication.models import DedupRelation
from datetime import timedelta
from enferno.utils.sheet_utils import SheetUtils

cfg = ProdConfig if os.environ.get('FLASK_DEBUG') == '0' else DevConfig



celery = Celery('tasks', broker=cfg.celery_broker_url)
# remove deprecated warning
celery.conf.update(
    {'accept_content': ['pickle', 'json', 'msgpack', 'yaml']})
celery.conf.update({'result_backend': os.environ.get('CELERY_RESULT_BACKEND', cfg.result_backend)})
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

# splitting db operations for performance
BULK_CHUNK_SIZE = 2

def chunk_list(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

@celery.task
def bulk_update_bulletins(ids, bulk, cur_user_id):
    # build mappings
    u = {'id': cur_user_id}
    cur_user = namedtuple('cur_user', u.keys())(*u.values())
    user = User.query.get(cur_user_id)
    chunks = chunk_list(ids,BULK_CHUNK_SIZE)

    for group in chunks:

        # Fetch bulletins
        bulletins = Bulletin.query.filter(Bulletin.id.in_(group))
        for bulletin in bulletins:

            # check user can access each bulletin
            if not user.can_access(bulletin):
                # Log?
                continue

            # get Status initially
            status = bulk.get('status')

            # Assigned user
            assigned_to_id = bulk.get('assigned_to_id')
            if assigned_to_id:
                bulletin.assigned_to_id = assigned_to_id
                if not status:
                    bulletin.status = 'Assigned'

            # FPR user
            first_peer_reviewer_id = bulk.get('first_peer_reviewer_id')
            if first_peer_reviewer_id:
                bulletin.first_peer_reviewer_id = first_peer_reviewer_id
                if not status:
                    bulletin.status = 'Peer Review Assigned'


            if status:
                bulletin.status = status

            # Ref
            ref = bulk.get('ref')
            if ref:
                if bulk.get('refReplace'):
                    bulletin.ref = ref
                else:
                    #merge refs / remove dups
                    bulletin.ref = list(set(bulletin.ref + ref))

            # Comment (required)
            bulletin.comments = bulk.get('comments','')

            # Access Roles
            roles = bulk.get('roles')
            replace_roles = bulk.get('rolesReplace')
            if replace_roles:
                if roles:
                    role_ids = list(map(lambda x:x.get('id'), roles))
                    #get actual roles objects
                    roles = Role.query.filter(Role.id.in_(role_ids)).all()
                    # assign directly to the bulletin
                    bulletin.roles = roles
                else:
                    #clear bulletin roles
                    bulletin.roles = []
            else:
                if roles:
                    # merge roles
                    role_ids = list(map(lambda x: x.get('id'), roles))
                    # get actual roles objects
                    roles = Role.query.filter(Role.id.in_(role_ids)).all()
                    # assign directly to the bulletin
                    bulletin.roles = list(set(bulletin.roles + roles))

            # add only to session
            db.session.add(bulletin)

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

        # commit session when a batch of items and revisions are added
        db.session.commit()


        # Record Activity
        updated = [b.to_mini() for b in bulletins]
        Activity.create(cur_user, Activity.ACTION_BULK_UPDATE, updated, 'bulletin')
        # perhaps allow a little time out
        time.sleep(.25)

    print("Bulletins Bulk Update Successful")


@celery.task
def bulk_update_actors(ids, bulk, cur_user_id):
    # build mappings
    u = {'id': cur_user_id}
    cur_user = namedtuple('cur_user', u.keys())(*u.values())
    user = User.query.get(cur_user_id)
    chunks = chunk_list(ids,BULK_CHUNK_SIZE)
    for group in chunks:

        # Fetch bulletins
        actors = Actor.query.filter(Actor.id.in_(group))
        for actor in actors:

            # check user can access each actor
            if not user.can_access(actor):
                # Log?
                continue

            # get Status initially
            status = bulk.get('status')

            # Assigned user
            assigned_to_id = bulk.get('assigned_to_id')
            if assigned_to_id:
                actor.assigned_to_id = assigned_to_id
                if not status:
                    actor.status = 'Assigned'

            # FPR user
            first_peer_reviewer_id = bulk.get('first_peer_reviewer_id')
            if first_peer_reviewer_id:
                actor.first_peer_reviewer_id = first_peer_reviewer_id
                if not status:
                    actor.status = 'Peer Review Assigned'


            if status:
                actor.status = status


            # Comment (required)
            actor.comments = bulk.get('comments','')

            # Access Roles
            roles = bulk.get('roles')
            replace_roles = bulk.get('rolesReplace')
            if replace_roles:
                if roles:
                    role_ids = list(map(lambda x: x.get('id'), roles))
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
                    role_ids = list(map(lambda x: x.get('id'), roles))
                    # get actual roles objects
                    roles = Role.query.filter(Role.id.in_(role_ids)).all()
                    # assign directly to the actor
                    actor.roles = list(set(actor.roles + roles))

            # add only to session
            db.session.add(actor)

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

        # commit session when a batch of items and revisions are added
        db.session.commit()


        # Record Activity
        updated = [b.to_mini() for b in actors]
        Activity.create(cur_user, Activity.ACTION_BULK_UPDATE, updated, 'actor')
        # perhaps allow a little time out
        time.sleep(.25)

    print("Actors Bulk Update Successful")


@celery.task
def bulk_update_incidents(ids, bulk, cur_user_id):
    # build mappings
    u = {'id': cur_user_id}
    cur_user = namedtuple('cur_user', u.keys())(*u.values())
    user = User.query.get(cur_user_id)
    chunks = chunk_list(ids, BULK_CHUNK_SIZE)

    # for ops on related items
    assign_related = bulk.get('assignRelated')
    restrict_related = bulk.get('restrictRelated')
    actors = []
    bulletins = []

    for group in chunks:

        # Fetch bulletins
        incidents = Incident.query.filter(Incident.id.in_(group))
        for incident in incidents:

            # check if user can access incident
            if not user.can_access(incident):
                # Log?
                continue

            # get Status initially
            status = bulk.get('status')

            # Assigned user
            assigned_to_id = bulk.get('assigned_to_id')
            if assigned_to_id:
                incident.assigned_to_id = assigned_to_id
                if not status:
                    incident.status = 'Assigned'

            # FPR user
            first_peer_reviewer_id = bulk.get('first_peer_reviewer_id')
            if first_peer_reviewer_id:
                incident.first_peer_reviewer_id = first_peer_reviewer_id
                if not status:
                    incident.status = 'Peer Review Assigned'

            if status:
                incident.status = status

            # Comment (required)
            incident.comments = bulk.get('comments', '')

            # Access Roles
            roles = bulk.get('roles')
            replace_roles = bulk.get('rolesReplace')
            if replace_roles:
                if roles:
                    role_ids = list(map(lambda x: x.get('id'), roles))
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
                    role_ids = list(map(lambda x: x.get('id'), roles))
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

        # commit session when a batch of items and revisions are added
        db.session.commit()

        # Record Activity
        updated = [b.to_mini() for b in incidents]
        Activity.create(cur_user, Activity.ACTION_BULK_UPDATE, updated, 'incident')

        # restrict or assign related items
        if assign_related or restrict_related:
            # remove status
            bulk.pop('status', None)

            # not assigning related items
            if not assign_related:
                bulk.pop('assigned_to_id', None)
                bulk.pop('first_peer_reviewer_id', None)

            # not restricting related items
            if not restrict_related:
                bulk.pop('roles', None)
                bulk.pop('rolesReplace', None)

            # carry out bulk ops on related items
            if len(actors):
                bulk_update_actors(actors, bulk, cur_user_id)
            if len(bulletins):
                bulk_update_bulletins(bulletins, bulk, cur_user_id)

        # perhaps allow a little time out
        time.sleep(.25)

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
        if rds.get('dedup') != b'1' or rds.scard('dedq') == 0:
            rds.delete('dedup')
            rds.publish('dedprocess', 0)
            # Pause processing / do nothing
            print("Process engine - off")
            return

        data = []
        items = rds.spop('dedq', cfg.DEDUP_BATCH_SIZE).decode('utf-8')
        for item in items:
            data = item.split('|')
            process_dedup.delay(data[0], data[1])

        update_stats()


@celery.task
def process_sheet(filepath, map, target, batch_id, vmap, sheet, actorConfig, lang, roles=[]):
    su = SheetUtils(filepath, actorConfig, lang)
    su.import_sheet(map, target, batch_id, vmap, sheet, roles)


def generate_user_roles():
    '''
    Generates standard user roles.
    '''
    # create admin role if it doesn't exist
    r = Role.query.filter_by(name='Admin').first()
    if not r:
        role = Role()
        role.name = 'Admin'
        role.description = 'System Role'
        role.save()

    # create DA role, if not exists
    r = Role.query.filter_by(name='DA').first()
    if not r:
        role = Role()
        role.name = 'DA'
        role.description = 'System Role'
        role.save()

    # create MOD role, if not exists
    r = Role.query.filter_by(name='Mod').first()
    if not r:
        role = Role()
        role.name = 'Mod'
        role.description = 'System Role'
        role.save()


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

def create_default_location_data():
    if not LocationAdminLevel.query.all():
        db.session.add(LocationAdminLevel(code=1, title='Governorate'))
        db.session.add(LocationAdminLevel(code=2, title='District'))
        db.session.add(LocationAdminLevel(code=3, title='Subdistrict'))
        db.session.add(LocationAdminLevel(code=4, title='Community'))
        db.session.add(LocationAdminLevel(code=5, title='Neighbourhood'))
        db.session.commit()

    if not LocationType.query.all():
        db.session.add(LocationType(title='Administrative Location'))
        db.session.add(LocationType(title='Point of Interest'))
        db.session.commit()
