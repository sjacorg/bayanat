import random
import factory
from uuid import uuid4

from geoalchemy2.shape import WKTElement


import pytest

from enferno.admin.models import (
    Activity,
    Actor,
    ActorHistory,
    ActorProfile,
    AppConfig,
    AtoaInfo,
    AtobInfo,
    BtobInfo,
    Bulletin,
    BulletinHistory,
    ClaimedViolation,
    Country,
    Ethnography,
    Event,
    Eventtype,
    GeoLocation,
    GeoLocationType,
    Incident,
    IncidentHistory,
    ItoaInfo,
    ItobInfo,
    ItoiInfo,
    Label,
    Location,
    LocationAdminLevel,
    LocationHistory,
    LocationType,
    MediaCategory,
    PotentialViolation,
    Query,
    Source,
)
from enferno.user.models import Role, User

# region: factory models


class ActorProfileFactory(factory.Factory):
    class Meta:
        model = ActorProfile

    originid = factory.Faker("ssn")
    description = factory.Faker("text")
    source_link = factory.Faker("uri")
    source_link_type = factory.LazyFunction(lambda: random.choice([True, False]))
    publish_date = factory.Faker("date")
    documentation_date = factory.Faker("date")


class ActorFactory(factory.Factory):
    class Meta:
        model = Actor

    type = "Entity"
    name_ar = factory.LazyAttribute(lambda obj: f"{obj.name} (Ar)")
    nickname = factory.Faker("user_name")
    nickname_ar = factory.LazyAttribute(lambda obj: f"{obj.nickname} (Ar)")
    first_name = factory.Faker("first_name")
    first_name_ar = factory.LazyAttribute(lambda obj: f"{obj.first_name} (Ar)")
    middle_name = factory.Faker("first_name")
    middle_name_ar = factory.LazyAttribute(lambda obj: f"{obj.middle_name} (Ar)")
    last_name = factory.Faker("last_name")
    last_name_ar = factory.LazyAttribute(lambda obj: f"{obj.last_name} (Ar)")
    name = factory.Faker("name")
    mother_name = factory.Faker("name_female")
    mother_name_ar = factory.LazyAttribute(lambda obj: f"{obj.mother_name} (Ar)")
    father_name = factory.Faker("name_male")
    father_name_ar = factory.LazyAttribute(lambda obj: f"{obj.father_name} (Ar)")
    sex = factory.LazyFunction(lambda: random.choice(["male", "female"]))
    age = factory.LazyFunction(lambda: random.randint(9, 99))
    civilian = factory.Faker("text", max_nb_chars=255)
    occupation = factory.Faker("job")
    occupation_ar = factory.LazyAttribute(lambda obj: f"{obj.occupation} (Ar)"[:255])
    position = factory.Faker("text", max_nb_chars=255)
    position_ar = factory.LazyAttribute(lambda obj: f"{obj.position} (Ar)"[:255])
    family_status = factory.Faker("text", max_nb_chars=255)
    no_children = factory.LazyFunction(lambda: random.randint(0, 10))
    id_number = factory.Faker("ssn")
    status = factory.Faker("text", max_nb_chars=255)
    comments = factory.Faker("text", max_nb_chars=255)
    review = factory.Faker("text")
    review_action = factory.Faker("text", max_nb_chars=255)


class ActorHistoryFactory(factory.Factory):
    class Meta:
        model = ActorHistory

    data = factory.Sequence(lambda n: {f"Key{n}": f"Value{n}"})


class BulletinFactory(factory.Factory):
    class Meta:
        model = Bulletin

    title = factory.Faker("text")
    title_ar = factory.LazyAttribute(lambda obj: f"{obj.title} (Ar)"[:255])
    sjac_title = factory.Faker("text", max_nb_chars=255)
    sjac_title_ar = factory.LazyAttribute(lambda obj: f"{obj.sjac_title} (Ar)"[:255])
    description = factory.Faker("text")
    reliability_score = factory.LazyFunction(lambda: random.randint(0, 5))
    publish_date = factory.Faker("date")
    documentation_date = factory.Faker("date")
    status = factory.Faker("text", max_nb_chars=255)
    source_link = factory.Faker("uri")
    source_link_type = factory.LazyFunction(lambda: random.choice([True, False]))
    ref = factory.LazyFunction(lambda: [])
    originid = factory.Faker("ssn")
    comments = factory.Faker("text")
    review = factory.Faker("text")
    review_action = factory.Faker("text", max_nb_chars=255)


class BulletinHistoryFactory(factory.Factory):
    class Meta:
        model = BulletinHistory

    data = factory.Sequence(lambda n: {f"Key{n}": f"Value{n}"})


class IncidentFactory(factory.Factory):
    class Meta:
        model = Incident

    title = factory.Sequence(lambda n: f"Incident {n}")
    title_ar = f"{title} (Ar)"
    description = factory.Faker("text")
    status = factory.Faker("text", max_nb_chars=255)
    comments = factory.Faker("text")
    review = factory.Sequence(lambda n: f"Incident review {n}")
    review_action = factory.Faker("text", max_nb_chars=255)


class IncidentHistoryFactory(factory.Factory):
    class Meta:
        model = IncidentHistory

    data = factory.Sequence(lambda n: {f"Key{n}": f"Value{n}"})


class LocationFactory(factory.Factory):
    class Meta:
        model = Location

    title = factory.Sequence(lambda n: f"Location {n}")
    latlng = factory.LazyFunction(
        lambda: WKTElement(
            f"POINT({random.uniform(-180.00000, 180.00000)} {random.uniform(-90.00000, 90.00000)})",
            srid=4326,
        )
    )


class LocationHistoryFactory(factory.Factory):
    class Meta:
        model = LocationHistory

    data = factory.Sequence(lambda n: {f"Key{n}": f"Value{n}"})


class LabelFactory(factory.Factory):
    class Meta:
        model = Label

    title = factory.Sequence(lambda n: f"Label {n}")
    for_actor = False
    for_bulletin = False
    for_incident = False
    for_offline = False
    verified = False
    comments = factory.Faker("sentence")


class EventtypeFactory(factory.Factory):
    class Meta:
        model = Eventtype

    title = factory.Sequence(lambda n: f"Eventtype {n}")
    title_ar = factory.LazyAttribute(lambda obj: f"{obj.title} (Ar)"[:255])
    comments = factory.Faker("paragraph")
    for_actor = False
    for_bulletin = False
    comments = factory.Faker("sentence")


class EventFactory(factory.Factory):
    class Meta:
        model = Event

    title = factory.Sequence(lambda n: f"Event {n}")
    title_ar = factory.LazyAttribute(lambda obj: f"{obj.title} (Ar)"[:255])
    comments = factory.Faker("text", max_nb_chars=255)
    comments_ar = factory.LazyAttribute(lambda obj: f"{obj.comments} (Ar)"[:255])
    from_date = factory.Faker("date")
    to_date = factory.Faker("date")
    estimated = random.choice([True, False])


class PotentialViolationFactory(factory.Factory):
    class Meta:
        model = PotentialViolation

    title = factory.Sequence(lambda n: f"PotentialViolation {n}")


class ClaimedViolationFactory(factory.Factory):
    class Meta:
        model = ClaimedViolation

    title = factory.Sequence(lambda n: f"ClaimedViolation {n}")


class SourceFactory(factory.Factory):
    class Meta:
        model = Source

    etl_id = factory.Faker("text")
    title = factory.Sequence(lambda n: f"Source {n}")
    title_ar = factory.LazyAttribute(lambda obj: f"{obj.title} (Ar)"[:255])
    source_type = factory.Faker("text", max_nb_chars=255)
    comments = factory.Faker("paragraph")
    comments_ar = factory.LazyAttribute(lambda obj: f"{obj.comments} (Ar)")


class LocationAdminLevelFactory(factory.Factory):
    class Meta:
        model = LocationAdminLevel

    code = factory.Sequence(lambda n: n)
    title = factory.Sequence(lambda n: f"LocationAdminLevel {n}")


class LocationTypeFactory(factory.Factory):
    class Meta:
        model = LocationType

    title = factory.Sequence(lambda n: f"LocationType {n}")


class CountryFactory(factory.Factory):
    class Meta:
        model = Country

    title = factory.Sequence(lambda n: f"Country {n}")


class EthnographyFactory(factory.Factory):
    class Meta:
        model = Ethnography

    title = factory.Sequence(lambda n: f"Ethnography {n}")


class AtoaInfoFactory(factory.Factory):
    class Meta:
        model = AtoaInfo

    title = factory.Sequence(lambda n: f"AtoaInfo {n}")
    reverse_title = factory.Sequence(lambda n: f"Reverse AtoaInfo {n}")


class AtobInfoFactory(factory.Factory):
    class Meta:
        model = AtobInfo

    title = factory.Sequence(lambda n: f"AtobInfo {n}")
    reverse_title = factory.Sequence(lambda n: f"Reverse AtobInfo {n}")


class BtobInfoFactory(factory.Factory):
    class Meta:
        model = BtobInfo

    title = factory.Sequence(lambda n: f"BtobInfo {n}")
    reverse_title = factory.Sequence(lambda n: f"Reverse BtobInfo {n}")


class ItoaInfoFactory(factory.Factory):
    class Meta:
        model = ItoaInfo

    title = factory.Sequence(lambda n: f"ItoaInfo {n}")
    reverse_title = factory.Sequence(lambda n: f"Reverse ItoaInfo {n}")


class ItobInfoFactory(factory.Factory):
    class Meta:
        model = ItobInfo

    title = factory.Sequence(lambda n: f"ItobInfo {n}")
    reverse_title = factory.Sequence(lambda n: f"Reverse ItobInfo {n}")


class ItoiInfoFactory(factory.Factory):
    class Meta:
        model = ItoiInfo

    title = factory.Sequence(lambda n: f"ItoiInfo {n}")
    reverse_title = factory.Sequence(lambda n: f"Reverse ItoiInfo {n}")


class MediaCategoryFactory(factory.Factory):
    class Meta:
        model = MediaCategory

    title = factory.Sequence(lambda n: f"MediaCategory {n}")
    title_tr = factory.Sequence(lambda n: f"MediaCategory Tr {n}")


class GeoLocationTypeFactory(factory.Factory):
    class Meta:
        model = GeoLocationType

    title = factory.Sequence(lambda n: f"GeoLocationType {n}")
    title_tr = factory.Sequence(lambda n: f"GeoLocationType Tr {n}")


class UserFactory(factory.Factory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"Uniqueuser{n}")
    password = factory.Sequence(lambda n: f"SecurePassword{n}!")
    email = factory.Faker("email")
    active = True
    name = factory.Sequence(lambda n: f"Name {n}")
    fs_uniquifier = uuid4().hex


class RoleFactory(factory.Factory):
    class Meta:
        model = Role

    name = factory.Sequence(lambda n: f"Role{n}")
    color = factory.Sequence(lambda n: f"Color{n}")
    description = factory.Sequence(lambda n: f"Description {n}")


class ActivityFactory(factory.Factory):
    class Meta:
        model = Activity

    action = factory.Sequence(lambda n: f"Activity action {n}")


class QueryFactory(factory.Factory):
    class Meta:
        model = Query

    name = factory.Sequence(lambda n: f"Query_{n}")
    query_type = factory.Faker("random_element", elements=Query.TYPES)
    data = {"key": "val"}


class AppConfigFactory(factory.Factory):
    class Meta:
        model = AppConfig

    config = {"config_key": "config_val"}


class GeoLocationFactory(factory.Factory):
    class Meta:
        model = GeoLocation

    title = factory.Sequence(lambda n: f"GeoLocation {n}")
    main = factory.Faker("boolean")
    latlng = factory.LazyFunction(
        lambda: WKTElement(
            f"POINT({random.uniform(-180.00000, 180.00000)} {random.uniform(-90.00000, 90.00000)})",
            srid=4326,
        )
    )
    comment = factory.Faker("text")


# endregion: factory models
# region: factory fixtures
##### LABELS #####


@pytest.fixture
def create_label_for(request, session):
    def _create_label(entity_type):
        label = LabelFactory()
        label.for_actor = entity_type.lower() == "actor"
        label.for_bulletin = entity_type.lower() == "bulletin"
        label.for_incident = entity_type.lower() == "incident"
        session.add(label)
        session.commit()
        request.addfinalizer(lambda: session.delete(label))
        return label

    return _create_label


@pytest.fixture
def create_ver_label_for(request, session):
    def _create_label(entity_type):
        label = LabelFactory()
        label.verified = True
        label.for_actor = entity_type.lower() == "actor"
        label.for_bulletin = entity_type.lower() == "bulletin"
        label.for_incident = entity_type.lower() == "incident"
        session.add(label)
        session.commit()
        request.addfinalizer(lambda: session.delete(label))
        return label

    return _create_label


##### SOURCES #####


@pytest.fixture(scope="function")
def create_source(session):
    source = SourceFactory()
    session.add(source)
    session.commit()
    yield source
    try:
        session.delete(source)
    except:
        pass


##### EVENTTYPES #####


@pytest.fixture
def create_eventtype_for(request, session):
    def _create_eventtype(entity_type):
        eventtype = EventtypeFactory()
        eventtype.for_actor = entity_type.lower() == "actor"
        eventtype.for_bulletin = entity_type.lower() == "bulletin"
        session.add(eventtype)
        session.commit()
        request.addfinalizer(lambda: session.delete(eventtype))
        return eventtype

    return _create_eventtype


##### LOCATIONS #####


@pytest.fixture(scope="function")
def create_location(session):
    from enferno.admin.models import LocationHistory

    location = LocationFactory()
    session.add(location)
    session.commit()
    yield location
    session.query(LocationHistory).filter(LocationHistory.location_id == location.id).delete(
        synchronize_session=False
    )
    session.delete(location)
    session.commit()


##### GEOLOCATIONS #####
@pytest.fixture(scope="function")
def create_geolocation(request, session):
    def _clean(geolocation):
        session.delete(geolocation)

    def _create_geolocation(bulletin_id, type_id=None):
        geolocation = GeoLocationFactory()
        if type_id is None:
            typ = session.query(GeoLocationType).first()
            if typ is None:
                typ = GeoLocationTypeFactory()
                session.add(typ)
                session.commit()
                request.addfinalizer(lambda: session.delete(typ))
        else:
            typ = session.query(GeoLocationType).filter(GeoLocationType.id == type_id).first()
        geolocation.type = typ
        b = session.query(Bulletin).filter(Bulletin.id == bulletin_id).first()
        geolocation.bulletin = b
        session.add(geolocation)
        session.commit()
        request.addfinalizer(lambda: _clean(geolocation))
        return geolocation

    return _create_geolocation


##### EVENTS #####


@pytest.fixture(scope="function")
def create_event_for(request, session, create_eventtype_for, create_location):
    def _clean(event, eventtype):
        session.delete(eventtype)
        session.delete(event)

    def _create_event(entity_type):
        event = EventFactory()
        eventtype = create_eventtype_for(entity_type)
        location = create_location
        event.eventtype = eventtype
        event.location = location
        session.add(event)
        session.commit()
        request.addfinalizer(lambda: _clean(event, eventtype))
        return event

    return _create_event


##### ACTORPROFILE #####


@pytest.fixture
def create_profile_for(request, session):
    def _create_profile(actor):
        profile = ActorProfileFactory()
        profile.actor = actor
        session.add(profile)
        session.commit()
        request.addfinalizer(lambda: session.delete(profile))
        return profile

    return _create_profile


# endregion: factory fixtures
