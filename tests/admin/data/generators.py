import json

import pytest

from enferno.admin.models import GeoLocationType
from tests.factories import (
    ActorFactory,
    BulletinFactory,
    IncidentFactory,
    create_event_for,
    create_label_for,
    create_ver_label_for,
    create_source,
    create_profile_for,
    create_geolocation,
)


##### ACTOR #####


@pytest.fixture(scope="function")
def create_simple_actor(session, users):
    actor = ActorFactory()
    session.add(actor)
    session.commit()
    yield actor


@pytest.fixture(scope="function")
def create_full_actor(
    session,
    users,
    create_label_for,
    create_ver_label_for,
    create_source,
    create_event_for,
    create_profile_for,
):
    actor = ActorFactory()
    user, _, _, _ = users
    actor.first_peer_reviewer = user
    actor.assigned_to = user
    profile = create_profile_for(actor)
    label = create_label_for("actor")
    ver_label = create_ver_label_for("actor")
    event = create_event_for("actor")
    profile.labels.append(label)
    profile.ver_labels.append(ver_label)
    profile.sources.append(create_source)
    actor.events.append(event)
    session.add(actor)
    session.commit()
    yield actor


@pytest.fixture(scope="function")
def create_related_actor(session):
    a1 = ActorFactory()
    a2 = ActorFactory()
    a3 = ActorFactory()
    session.add_all([a1, a2, a3])
    session.commit()
    a2.relate_actor(a1, json.dumps({}), False)
    a3.relate_actor(a1, json.dumps({}), False)
    yield a1, a2, a3


##### INCIDENTS #####


@pytest.fixture(scope="function")
def create_simple_incident(session):
    incident = IncidentFactory()
    session.add(incident)
    session.commit()
    yield incident


@pytest.fixture(scope="function")
def create_full_incident(session, users, create_label_for):
    incident = IncidentFactory()
    user, _, _, _ = users
    incident.first_peer_reviewer = user
    incident.assigned_to = user

    label = create_label_for("incident")
    incident.labels.append(label)

    session.add(incident)
    session.commit()
    yield incident


@pytest.fixture(scope="function")
def create_related_incident(session):
    i1 = IncidentFactory()
    i2 = IncidentFactory()
    i3 = IncidentFactory()
    session.add_all([i1, i2, i3])
    session.commit()
    i2.relate_incident(i1, json.dumps({}), False)
    i3.relate_incident(i1, json.dumps({}), False)
    yield i1, i2, i3


##### BULLETINS ######


@pytest.fixture(scope="function")
def create_simple_bulletin(session):
    bulletin = BulletinFactory()
    session.add(bulletin)
    session.commit()
    yield bulletin


@pytest.fixture(scope="function")
def create_full_bulletin(
    request,
    session,
    users,
    create_label_for,
    create_ver_label_for,
    create_source,
    create_event_for,
    create_geolocation,
):
    bulletin = BulletinFactory()
    user, _, _, _ = users
    bulletin.first_peer_reviewer = user
    bulletin.assigned_to = user
    label = create_label_for("bulletin")
    ver_label = create_ver_label_for("bulletin")
    event = create_event_for("bulletin")
    bulletin.labels.append(label)
    bulletin.sources.append(create_source)
    bulletin.ver_labels.append(ver_label)
    bulletin.events.append(event)
    geoloc = create_geolocation(bulletin.id)
    bulletin.geo_locations.append(geoloc)
    session.add(bulletin)
    session.commit()
    yield bulletin


@pytest.fixture(scope="function")
def create_related_bulletin(session):
    b1 = BulletinFactory()
    b2 = BulletinFactory()
    b3 = BulletinFactory()
    session.add_all([b1, b2, b3])
    session.commit()
    b2.relate_bulletin(b1, json.dumps({}), False)
    b3.relate_bulletin(b1, json.dumps({}), False)
    yield b1, b2, b3
