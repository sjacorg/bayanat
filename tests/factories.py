import random
import factory
from uuid import uuid4
from enferno.admin.models import (
    Activity,
    Actor,
    ActorHistory,
    AppConfig,
    AtoaInfo,
    AtobInfo,
    BtobInfo,
    Bulletin,
    BulletinHistory,
    ClaimedViolation,
    Country,
    Ethnography,
    Eventtype,
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


class ActorFactory(factory.Factory):
    class Meta:
        model = Actor

    name = factory.Sequence(lambda n: f"Actor {n}")
    age = 25
    type = "Entity"
    review = factory.Sequence(lambda n: f"Actor review {n}")


class ActorHistoryFactory(factory.Factory):
    class Meta:
        model = ActorHistory

    data = factory.Sequence(lambda n: {f"Key{n}": f"Value{n}"})


class BulletinFactory(factory.Factory):
    class Meta:
        model = Bulletin

    title = factory.Sequence(lambda n: f"Bulletin {n}")
    ref = []
    review = factory.Sequence(lambda n: f"Bulletin review {n}")


class BulletinHistoryFactory(factory.Factory):
    class Meta:
        model = BulletinHistory

    data = factory.Sequence(lambda n: {f"Key{n}": f"Value{n}"})


class IncidentFactory(factory.Factory):
    class Meta:
        model = Incident

    title = factory.Sequence(lambda n: f"Location {n}")
    review = factory.Sequence(lambda n: f"Incident review {n}")


class IncidentHistoryFactory(factory.Factory):
    class Meta:
        model = IncidentHistory

    data = factory.Sequence(lambda n: {f"Key{n}": f"Value{n}"})


class LocationFactory(factory.Factory):
    class Meta:
        model = Location

    title = factory.Sequence(lambda n: f"Location {n}")


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


class EventtypeFactory(factory.Factory):
    class Meta:
        model = Eventtype

    title = factory.Sequence(lambda n: f"Eventtype {n}")
    for_actor = False
    for_bulletin = False


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

    title = factory.Sequence(lambda n: f"Source {n}")


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
    query_type = random.choice(["bulletin", "incident", "actor"])
    data = {"key": "val"}


class AppConfigFactory(factory.Factory):
    class Meta:
        model = AppConfig

    config = {"config_key": "config_val"}
