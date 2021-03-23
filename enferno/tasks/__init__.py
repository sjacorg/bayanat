# -*- coding: utf-8 -*-

import os
import random
import time
from collections import namedtuple
from datetime import timedelta

import pandas as pd
from celery import Celery
from celery.task import periodic_task
from faker import Faker
from flask_security.utils import hash_password
from sqlalchemy import func

from enferno.admin.models import Bulletin, Label, Source, Location, Event, Eventtype, Actor, PotentialViolation, \
    ClaimedViolation, Incident, BulletinHistory, Activity, ActorHistory, IncidentHistory
from enferno.extensions import db
from enferno.settings import ProdConfig, DevConfig
from enferno.user.models import User, Role
from flask_security.utils import hash_password

celery = Celery(__name__)

# Load configuraitons based on environment settings
if os.environ.get("FLASK_DEBUG") == '0':
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

def generate_users(num=6):
    faker = Faker()
    if User.query.count() > 3:
        return
    for i in range(1, num):
        u = User()
        u.email = 'demo' + str(i) + '@sjac.com'
        u.name = 'demo ' + str(i)
        u.password = hash_password('your-strong-pass-here-@@##@@')
        u.active = 1
        u.save()


faker = Faker()
fakar = Faker(['ar_SA'])


@celery.task
def generate_bulletin(item: pd):
    try:
        b = Bulletin()
        # b.id = item['id']
        b.title = item['title_en']
        b.title_ar = item['title_ar']
        b.sjac_title = item['sjac_title_en']
        b.sjac_title_ar = item['sjac_title_ar']
        b.description = item['description_en']
        b.originid = item['origin_id']

        two_users = User.query.order_by(func.random())[:2]
        b.assigned_to_id = two_users[0].id
        b.first_peer_reviewer_id = two_users[1].id
        # assign workflow to a random state
        if random.randint(1, 2) % 2:
            b.status = 'Assigned'
        else:
            b.status = 'Peer Review Assigned'

        # gen some arabic fields (use chinese temporarily as the library doesn't support arabic locale)
        b.comments = 'Created (Random Script)'

        # some labels
        for i in range(3):
            l = Label.query.order_by(func.random()).first()
            if l not in b.labels:
                b.labels.append(l)

        # some sources
        for i in range(3):
            s = Source.query.order_by(func.random()).first()
            if s not in b.sources:
                b.sources.append(s)

        # some locations
        for i in range(3):
            l = Location.query.order_by(func.random()).first()
            if l not in b.locations:
                b.locations.append(l)

        # some events
        for i in range(4):
            e = Event()
            e.title = faker.sentence()
            l = Location.query.order_by(func.random()).first()
            t = Eventtype.query.order_by(func.random()).first()
            e.eventtype = t
            e.location = l
            e.save()
            b.events.append(e)

        b.status = 'Machine Created'

        # relate some bulletins/actors/incidents

        b.save()
        b.create_revision(user_id=1)
        print('Generated bulletin ... {}'.format(b.id))
    except Exception as e:
        print(e)






@celery.task
def generate_actor(item):
    try:
        a = Actor()
        a.id = item['id']
        a.name = item['fullname_en']
        a.name_ar = item['fullname_ar']
        a.first_name = item['first_name_en']
        a.first_name_ar = item['first_name_ar']
        a.last_name = item['last_name_en']
        a.last_name_ar = item['last_name_ar']
        a.occupation = item['occupation_en']
        a.description = item['description_en']
        a.description_ar = item['description_ar']
        a.originid = item['origin_id']

        a.actor_type = random.choice(['Person', 'Entity'])
        a.sex = random.choice(['Male', 'Female'])
        a.age = random.choice(['Minor', 'Adult', 'Unknown'])
        a.civilian = random.choice(['Unknown', 'Civilian', 'Non-Civilian', 'Police', 'Other Security Forces'])
        a.ethnography = [random.choice(
            ['Alawite', 'Arab', 'Armenian', 'Christian', 'Circassian', 'Druze', 'Ismaili', 'Kurd', 'Shiaa', 'Sunni',
             'Syriac', 'Turkmen', 'Unknown'])]

        l = Location.query.order_by(func.random()).first()
        a.birth_place_id = l.id
        l = Location.query.order_by(func.random()).first()
        a.residence_place_id = l.id

        # gen some arabic fields (use chinese temporarily as the library doesn't support arabic locale)
        a.name_ar = fakar.name()

        two_users = User.query.order_by(func.random())[:2]
        a.assigned_to_id = two_users[0].id
        a.first_peer_reviewer_id = two_users[1].id

        # some labels
        for i in range(3):
            l = Label.query.order_by(func.random()).first()
            if l not in a.labels:
                a.labels.append(l)

        # some sources
        for i in range(3):
            s = Source.query.order_by(func.random()).first()
            if s not in a.sources:
                a.sources.append(s)

        # some events
        for i in range(4):
            e = Event()
            e.title = faker.sentence()
            l = Location.query.order_by(func.random()).first()
            t = Eventtype.query.order_by(func.random()).first()
            e.eventtype = t
            e.location = l
            e.save()
            a.events.append(e)
        a.comments = 'Created (Random Script)'
        a.save()
        a.create_revision(user_id=1)
        print('Generated Actor ... {}'.format(a.id))
    except Exception as e:
        print(e)




@celery.task
def generate_incident():
    try:
        i = Incident()
        i.title = faker.sentence()
        i.description = faker.sentence()

        # gen some arabic fields (use chinese temporarily as the library doesn't support arabic locale)
        i.title_ar = fakar.sentence()
        i.comments = 'Created (Random Script)'

        # some labels
        for x in range(2):
            pv = PotentialViolation.query.order_by(func.random()).first()
            if pv not in i.potential_violations:
                i.potential_violations.append(pv)

        # some labels
        for x in range(2):
            cv = ClaimedViolation.query.order_by(func.random()).first()
            if cv not in i.claimed_violations:
                i.claimed_violations.append(cv)

        # some labels
        for x in range(3):
            l = Label.query.order_by(func.random()).first()
            if l not in i.labels:
                i.labels.append(l)

        # some locations
        for x in range(3):
            l = Location.query.order_by(func.random()).first()
            if l not in i.locations:
                i.locations.append(l)

        # some events
        for x in range(4):
            e = Event()
            e.title = faker.sentence()
            l = Location.query.order_by(func.random()).first()
            t = Eventtype.query.order_by(func.random()).first()
            e.eventtype = t
            e.location = l
            e.save()
            i.events.append(e)
        i.status = 'Machine Created'
        i.save()
        i.create_revision(user_id=1)
        print('Generated Incident ... {}'.format(i.id))
    except Exception as e:
        print(e)


def generate_incidents(num=20):
    for i in range(num):
        generate_incident.delay()


def generate_relations():
    print('generating some random relationships')

    # b2b
    # pick random sample
    sample = Bulletin.query.count() / 2
    bulletins = Bulletin.query.order_by(func.random()).limit(sample)
    for bulletin in bulletins:
        # 0 - 3 related entities
        x = Bulletin.query.order_by(func.random()).limit(random.randint(0, 3))
        for b in x:
            bulletin.relate_bulletin(b)
        bulletin.comments = 'added relationship'
        bulletin.create_revision()
    # b2a
    # pick random sample
    sample = Bulletin.query.count() / 2
    bulletins = Bulletin.query.order_by(func.random()).limit(sample)
    for bulletin in bulletins:
        # 0 - 3 related entities
        x = Actor.query.order_by(func.random()).limit(random.randint(0, 3))
        for a in x:
            bulletin.relate_actor(a)
            a.create_revision()
        bulletin.comments = 'added relationship with actor'
        bulletin.create_revision()
    # a2a
    # pick random sample
    sample = Actor.query.count() / 2
    actors = Actor.query.order_by(func.random()).limit(sample)
    for actor in actors:
        # 0 - 3 related entities
        x = Actor.query.order_by(func.random()).limit(random.randint(0, 3))
        for a in x:
            actor.relate_actor(a)
        actor.comments = 'added relationship'
        actor.create_revision()


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
            tmp['ref'] = refs + tmp.get('ref',[])

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


