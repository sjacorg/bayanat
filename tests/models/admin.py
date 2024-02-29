from typing import ForwardRef, Optional, List, Dict
from pydantic import BaseModel, Field
from tests.models.user import UserCompactModel, RoleModel, UserItemModel

## PYDANTIC MODELS ##


class LocationTypeModel(BaseModel):
    id: int
    title: str
    description: Optional[str]


class AdminLevelModel(BaseModel):
    id: int
    code: int
    description: Optional[str]


class CountryModel(BaseModel):
    id: int
    title: str
    title_tr: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


class LocationItemModel(BaseModel):
    id: int
    title: Optional[str]
    title_ar: Optional[str]
    description: Optional[str]
    location_type: Optional[LocationTypeModel]
    admin_level: Optional[AdminLevelModel]
    latlng: Optional[Dict[str, float]] = Field(None, alias="latlng")
    postal_code: Optional[str]
    country: Optional[CountryModel]
    parent: Optional[ForwardRef("LocationItemModel")]
    tags: List[str] = []
    lat: Optional[float]
    lng: Optional[float]
    full_location: Optional[str]
    full_string: Optional[str]
    updated_at: Optional[str]


# Because parent field self-references, we need to handle forward refs
LocationItemModel.update_forward_refs()


class LocationResponseModel(BaseModel):
    items: list[LocationItemModel]
    perPage: int
    total: int


class LocationRequestModel(BaseModel):
    item: Dict


class ActorItemMinModel(BaseModel):
    id: int
    title: str = Field(None, max_length=255)
    name: Optional[str] = Field(None, max_length=255)
    assigned_to: Optional["UserCompactModel"]
    first_peer_reviewer: Optional["UserCompactModel"]
    status: Optional[str] = Field(None, max_length=255)
    u_status: Optional[str] = Field(..., alias="_status")  # since status field is optional
    roles: Optional[List["RoleModel"]]


class SourcesJSONModel(BaseModel):
    id: int
    title: Optional[str]


class LabelsJSONModel(BaseModel):
    id: int
    title: Optional[str]


class VerLabelsJSONModel(BaseModel):
    id: int
    title: Optional[str]


class ActorItemMode2Model(BaseModel):
    class_: str = Field("Actor", alias="class")
    id: int
    originid: Optional[str] = Field(None, max_length=255)
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str]
    comments: Optional[str]
    sources: Optional[List["SourcesJSONModel"]]
    publish_date: Optional[str]
    documentation_date: Optional[str]
    status: Optional[str] = Field(None, max_length=255)


class EthnographyModel(BaseModel):
    id: int
    title: str
    title_tr: Optional[str]
    created_at: str
    updated_at: str


class EventTypeModel(BaseModel):
    id: int
    title: Optional[str]
    title_ar: Optional[str]
    for_actor: bool = False
    for_bulletin: bool = False
    comments: Optional[str]
    updated_at: str


class EventModel(BaseModel):
    id: int
    title: Optional[str]
    title_ar: Optional[str]
    comments: Optional[str]
    comments_ar: Optional[str]
    location: Optional[LocationItemModel]
    eventtype: Optional[EventTypeModel]
    from_date: str
    to_date: str
    estimated: Optional[bool]
    updated_at: str


class MediaModel(BaseModel):
    id: int
    title: Optional[str] = None
    title_ar: Optional[str] = None
    fileType: Optional[str] = Field(None, alias="media_file_type")
    filename: Optional[str] = Field(None, alias="media_file")
    etag: Optional[str] = None
    time: Optional[float] = None
    duration: Optional[str] = None
    main: bool = False
    updated_at: Optional[str] = None


class ActorItemMode3Model(BaseModel):
    class_: str = Field(..., alias="class")  # nolimit
    id: int
    originid: Optional[str] = Field(None, max_length=255)
    name: Optional[str] = Field(None, max_length=255)
    name_ar: Optional[str] = Field(None, max_length=255)
    description: Optional[str]  # nolimit
    nickname: Optional[str] = Field(None, max_length=255)
    nickname_ar: Optional[str] = Field(None, max_length=255)
    first_name: Optional[str] = Field(None, max_length=255)
    first_name_ar: Optional[str] = Field(None, max_length=255)
    middle_name: Optional[str] = Field(None, max_length=255)
    middle_name_ar: Optional[str] = Field(None, max_length=255)
    last_name: Optional[str] = Field(None, max_length=255)
    last_name_ar: Optional[str] = Field(None, max_length=255)
    mother_name: Optional[str] = Field(None, max_length=255)
    mother_name_ar: Optional[str] = Field(None, max_length=255)
    sex: Optional[str] = Field(None, max_length=255)
    u_sex: Optional[str] = Field(..., alias="_sex")  # nolimit
    age: Optional[str] = Field(None, max_length=255)
    u_age: Optional[str] = Field(..., alias="_age")  # nolimit
    civilian: Optional[str] = Field(None, max_length=255)
    u_civilian: Optional[str] = Field(..., alias="_civilian")  # nolimit
    actor_type: Optional[str] = Field(None, max_length=255)
    u_actor_type: Optional[str] = Field(..., alias="_actor_type")  # nolimit
    occupation: Optional[str] = Field(None, max_length=255)
    occupation_ar: Optional[str] = Field(None, max_length=255)
    position: Optional[str] = Field(None, max_length=255)
    position_ar: Optional[str] = Field(None, max_length=255)
    dialects: Optional[str] = Field(None, max_length=255)
    dialects_ar: Optional[str] = Field(None, max_length=255)
    family_status: Optional[str] = Field(None, max_length=255)
    family_status_ar: Optional[str] = Field(None, max_length=255)
    ethnography: List[EthnographyModel] = []
    nationality: List[CountryModel] = []
    national_id_card: Optional[str] = Field(None, max_length=255)
    assigned_to: Optional["UserCompactModel"]
    first_peer_reviewer: Optional["UserCompactModel"]
    source_link: Optional[str] = Field(None, max_length=255)
    source_link_type: Optional[bool] = False
    comments: Optional[str]  # nolimit
    sources: Optional[List["SourcesJSONModel"]] = []
    labels: Optional[List[LabelsJSONModel]] = []
    verLabels: Optional[List[VerLabelsJSONModel]] = []
    events: Optional[List[EventModel]] = []
    medias: Optional[List[MediaModel]] = []
    actor_relations: Optional[List] = []  # Lazy load in mode3
    bulletin_relations: Optional[List] = []  # Lazy load in mode3
    incident_relations: Optional[List] = []  # Lazy load in mode3
    birth_place: Optional[LocationItemModel]
    residence_place: Optional[LocationItemModel]
    origin_place: Optional[LocationItemModel]
    birth_date: Optional[str]
    publish_date: Optional[str]
    documentation_date: Optional[str]
    status: Optional[str] = Field(None, max_length=255)
    review: Optional[str]  # nolimit
    review_action: Optional[str]  # nolimit
    updated_at: Optional[str]
    roles: List[RoleModel] = []


class ActorCompactModel(BaseModel):
    id: int
    name: Optional[str] = Field(None, max_length=255)
    originid: Optional[str] = Field(None, max_length=255)
    sources: Optional[SourcesJSONModel]
    description: Optional[str]
    source_link: Optional[str] = Field(None, max_length=255)
    source_link_type: Optional[bool] = False
    publish_date: str
    documentation_date: str


class LocationsJSONModel(BaseModel):
    id: int
    title: Optional[str]
    full_string: Optional[str]
    lat: Optional[float]
    lng: Optional[float]


class BulletinCompactModel(BaseModel):
    id: int
    title: str = Field(None, max_length=255)
    title_ar: Optional[str] = Field(None, max_length=255)
    sjac_title: Optional[str] = Field(None, max_length=255)
    sjac_title_ar: Optional[str] = Field(None, max_length=255)
    originid: Optional[str]
    locations: Optional[LocationsJSONModel] = []
    sources: Optional[SourcesJSONModel] = []
    description: Optional[str]
    source_link: Optional[str] = Field(None, max_length=255)
    source_link_type: Optional[bool] = False
    publish_date: str
    documentation_date: str
    comments: Optional[str] = ""


class AtobModel(BaseModel):
    bulletin: BulletinCompactModel
    actor: ActorCompactModel
    related_as: Optional[List[int]] = []
    probability: Optional[int]
    comment: Optional[str]
    user_id: Optional[int]


class AtoaModel(BaseModel):
    actor: ActorCompactModel
    related_as: Optional[int]
    probability: Optional[int]
    comment: Optional[str]
    user_id: Optional[int]


class IncidentItemCompactModel(BaseModel):
    id: int
    title: str = Field(None, max_length=255)
    description: Optional[str]


class ItoaModel(BaseModel):
    actor: ActorCompactModel
    incident: IncidentItemCompactModel
    related_as: Optional[List[int]] = []
    probability: Optional[int]
    comment: Optional[str]
    user_id: Optional[int]


class ActorItemMode3PlusModel(ActorItemMode3Model):
    bulletin_relations: Optional[List[AtobModel]] = []
    actor_relations: Optional[List[AtoaModel]] = []
    incident_relations: Optional[List[ItoaModel]] = []


class ActorsResponseModel(BaseModel):
    items: List[
        ActorItemMinModel | ActorItemMode2Model | ActorItemMode3Model | ActorItemMode3PlusModel
    ]
    perPage: int
    total: int


class ActorRequestModel(BaseModel):
    item: Dict


class BulletinItemMinModel(BaseModel):
    id: int
    title: str = Field(None, max_length=255)
    name: Optional[str] = Field(None, max_length=255)
    assigned_to: Optional["UserCompactModel"]
    first_peer_reviewer: Optional["UserCompactModel"]
    status: Optional[str] = Field(None, max_length=255)
    u_status: Optional[str] = Field(..., alias="_status")
    roles: Optional[List["RoleModel"]]


class LocationItemCompactModel(BaseModel):
    id: int
    title: Optional[str]
    full_string: Optional[str]
    lat: Optional[float]
    lng: Optional[float]


class BulletinItemMode2Model(BaseModel):
    class_: str = Field("Bulletin", alias="class")
    id: int
    title: str
    title_ar: Optional[str]
    sjac_title: Optional[str]
    sjac_title_ar: Optional[str]
    originid: Optional[str]
    locations: List[LocationItemCompactModel]
    sources: List[SourcesJSONModel]
    description: Optional[str]
    comments: Optional[str]
    source_link: Optional[str]
    publish_date: Optional[str]
    documentation_date: Optional[str]


class GeoLocationTypeItemModel(BaseModel):
    id: int
    title: str
    title_tr: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


class GeoLocationItemModel(BaseModel):
    id: int
    title: Optional[str]
    type_id: Optional[int]
    type_: Optional[GeoLocationTypeItemModel] = Field(..., alias="type")
    main: Optional[bool]
    lat: Optional[float]
    lng: Optional[float]
    comment: Optional[str]
    updated_at: Optional[str]


class BulletinItemMode3Model(BaseModel):
    class_: str = Field(..., alias="class")
    id: int
    title: str
    title_ar: Optional[str]
    sjac_title: Optional[str]
    sjac_title_ar: Optional[str]
    originid: Optional[str]
    assigned_to: Optional[UserCompactModel]
    first_peer_reviewer: Optional[UserCompactModel]
    locations: Optional[List[LocationItemCompactModel]]
    geoLocations: Optional[List[GeoLocationItemModel]]
    labels: Optional[List[LabelsJSONModel]]
    verLabels: Optional[List[LabelsJSONModel]]
    sources: Optional[List[SourcesJSONModel]]
    events: Optional[List[EventModel]]
    medias: Optional[List[MediaModel]]
    bulletin_relations: Optional[List[Dict]] = []  # Lazy loading in mode 3
    actor_relations: Optional[List[Dict]] = []  # Lazy loading in mode 3
    incident_relations: Optional[List[Dict]] = []  # Lazy loading in mode 3
    description: Optional[str]
    comments: Optional[str]
    source_link: Optional[str]
    source_link_type: Optional[bool]
    ref: Optional[List[str]]
    publish_date: Optional[str]
    documentation_date: Optional[str]
    status: Optional[str]
    review: Optional[str]
    review_action: Optional[str]
    updated_at: Optional[str]
    roles: List[RoleModel]


class BtobModel(BaseModel):
    bulletin: BulletinCompactModel
    related_as: Optional[List[int]]
    probability: Optional[int]
    comment: Optional[str]
    user_id: Optional[int]


class ItobModel(BaseModel):
    incident: IncidentItemCompactModel
    bulletin: BulletinCompactModel
    related_as: Optional[int]
    probability: Optional[int]
    comment: Optional[str]
    user_id: Optional[int]


class BulletinItemMode3PlusModel(BulletinItemMode3Model):
    bulletin_relations: Optional[List[BtobModel]] = []
    actor_relations: Optional[List[AtobModel]] = []
    incident_relations: Optional[List[ItobModel]] = []


class BulletinsResponseModel(BaseModel):
    items: list[
        BulletinItemMinModel
        | BulletinItemMode2Model
        | BulletinItemMode3Model
        | BulletinItemMode3PlusModel
    ]
    perPage: int
    total: int


class BulletinRequestModel(BaseModel):
    item: Dict


class IncidentItemRestrictedModel(BaseModel):
    id: int
    restricted: bool = True


class IncidentItemMinModel(BaseModel):
    id: int
    title: str = Field(None, max_length=255)
    name: Optional[str] = Field(None, max_length=255)
    assigned_to: Optional["UserCompactModel"]
    first_peer_reviewer: Optional["UserCompactModel"]
    status: Optional[str] = Field(None, max_length=255)
    u_status: Optional[str] = Field(..., alias="_status")  # since status field is optional
    roles: Optional[List["RoleModel"]]


class LocationItemMinModel(BaseModel):
    id: int
    location_type: Optional[str | LocationTypeModel] = ""
    full_string: Optional[str]


class IncidentItemMode2Model(BaseModel):
    class_: str = Field("Incident", alias="class")
    id: int
    title: Optional[str]
    description: Optional[str]
    labels: List[LabelsJSONModel] = []
    locations: List[LocationItemMinModel] = []
    comments: Optional[str]
    status: Optional[str]


class PotentialViolationJSONModel(BaseModel):
    id: int
    title: Optional[str]


class ClaimedViolationJSONModel(BaseModel):
    id: int
    title: Optional[str]


class IncidentItemMode3Model(BaseModel):
    class_: str = Field(..., alias="class")
    id: int
    title: Optional[str]
    title_ar: Optional[str]
    description: Optional[str]
    assigned_to: Optional[UserCompactModel]
    first_peer_reviewer: Optional[UserCompactModel]
    labels: List[LabelsJSONModel] = []
    locations: List[LocationItemCompactModel] = []
    potential_violations: List[PotentialViolationJSONModel] = []
    claimed_violations: List[ClaimedViolationJSONModel] = []
    events: List[EventModel] = []
    actor_relations: List[Dict] = []  # Lazy load in mode 3
    bulletin_relations: List[Dict] = []  # Lazy load in mode 3
    incident_relations: List[Dict] = []  # Lazy load in mode 3
    comments: Optional[str]
    status: Optional[str]
    review: Optional[str]
    review_action: Optional[str]
    updated_at: str
    roles: List[RoleModel] = []


class ItoiModel(BaseModel):
    incident: IncidentItemCompactModel
    related_as: Optional[int]
    probability: Optional[int]
    comment: Optional[str]
    user_id: Optional[int]


class IncidentItemMode3PlusModel(IncidentItemMode3Model):
    actor_relations: List[ItoaModel] = []
    bulletin_relations: List[ItobModel] = []
    incident_relations: List[ItoiModel] = []


class IncidentsResponseModel(BaseModel):
    items: List[
        IncidentItemRestrictedModel
        | IncidentItemMinModel
        | IncidentItemMode2Model
        | IncidentItemMode3Model
        | IncidentItemMode3PlusModel
    ]
    perPage: int
    total: int


class IncidentRequestModel(BaseModel):
    item: Dict


class LabelMode2Model(BaseModel):
    id: int
    title: Optional[str]


class LabelModel(LabelMode2Model):
    title_ar: Optional[str]
    comments: Optional[str]
    comments_ar: Optional[str]
    order: Optional[int]
    verified: Optional[bool] = Field(False)
    for_bulletin: Optional[bool] = Field(False)
    for_actor: Optional[bool] = Field(False)
    for_incident: Optional[bool] = Field(False)
    for_offline: Optional[bool] = Field(False)
    parent: Optional[LabelMode2Model]
    updated_at: Optional[str]


class LabelsResponseModel(BaseModel):
    items: List[LabelMode2Model | LabelModel]
    perPage: int
    total: int


class EventTypeItemModel(BaseModel):
    id: int
    title: Optional[str]
    title_ar: Optional[str]
    for_actor: Optional[bool] = Field(False)
    for_bulletin: Optional[bool] = Field(False)
    comments: Optional[str]
    updated_at: Optional[str]


class EventtypesResponseModel(BaseModel):
    items: List[EventTypeItemModel]
    perPage: int
    total: int


class PotentialViolationItemModel(BaseModel):
    id: int
    title: Optional[str]


class PotentialViolationsResponseModel(BaseModel):
    items: List[PotentialViolationItemModel]
    perPage: int
    total: int


class ClaimedViolationItemModel(BaseModel):
    id: int
    title: Optional[str]


class ClaimedViolationsResponseModel(BaseModel):
    items: List[ClaimedViolationItemModel]
    perPage: int
    total: int


class SourceItemModel(BaseModel):
    id: int
    etl_id: Optional[str]
    title: Optional[str]
    parent: Optional[SourcesJSONModel]
    comments: Optional[str]
    updated_at: Optional[str]


class SourcesResponseModel(BaseModel):
    items: List[SourceItemModel]
    perPage: int
    total: int


class LocationAdminLevelItemModel(BaseModel):
    id: int
    code: int
    title: Optional[str]


class LocationAdminLevelsResponseModel(BaseModel):
    items: List[LocationAdminLevelItemModel]
    perPage: int
    total: int


class LocationTypesResponseModel(BaseModel):
    items: List[LocationTypeModel]
    perPage: int
    total: int


class CountriesResponseModel(BaseModel):
    items: List[CountryModel]
    perPage: int
    total: int


class EthnographiesResponseModel(BaseModel):
    items: List[EthnographyModel]
    perPage: int
    total: int


class AtoaInfoItemModel(BaseModel):
    id: int
    title: str
    reverse_title: str
    title_tr: Optional[str]
    reverse_title_tr: Optional[str]


class AtoaInfosResponseModel(BaseModel):
    items: List[AtoaInfoItemModel]
    perPage: int
    total: int


class AtobInfoItemModel(BaseModel):
    id: int
    title: str
    reverse_title: str
    title_tr: Optional[str]
    reverse_title_tr: Optional[str]


class AtobInfosResponseModel(BaseModel):
    items: List[AtobInfoItemModel]
    perPage: int
    total: int


class BtobInfoItemModel(BaseModel):
    id: int
    title: str
    reverse_title: str
    title_tr: Optional[str]
    reverse_title_tr: Optional[str]


class BtobInfosResponseModel(BaseModel):
    items: List[BtobInfoItemModel]
    perPage: int
    total: int


class ItoaInfoItemModel(BaseModel):
    id: int
    title: str
    reverse_title: str
    title_tr: Optional[str]
    reverse_title_tr: Optional[str]


class ItoaInfosResponseModel(BaseModel):
    items: List[ItoaInfoItemModel]
    perPage: int
    total: int


class ItobInfoItemModel(BaseModel):
    id: int
    title: str
    reverse_title: str
    title_tr: Optional[str]
    reverse_title_tr: Optional[str]


class ItobInfosResponseModel(BaseModel):
    items: List[ItobInfoItemModel]
    perPage: int
    total: int


class ItoiInfoItemModel(BaseModel):
    id: int
    title: str
    reverse_title: str
    title_tr: Optional[str]
    reverse_title_tr: Optional[str]


class ItoiInfosResponseModel(BaseModel):
    items: List[ItoiInfoItemModel]
    perPage: int
    total: int


class MediaCategoryItemModel(BaseModel):
    id: int
    title: str
    title_tr: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


class MediaCategoriesResponseModel(BaseModel):
    items: List[MediaCategoryItemModel]
    perPage: int
    total: int


class GeoLocationTypesResponseModel(BaseModel):
    items: List[MediaCategoryItemModel]
    perPage: int
    total: int


class HistoryHelperItemModel(BaseModel):
    id: int
    data: Optional[Dict]
    created_at: str
    updated_at: Optional[str]
    user: Optional[UserCompactModel]


class HistoryHelpersResponseModel(BaseModel):
    items: List[HistoryHelperItemModel]


class UsersResponseModel(BaseModel):
    items: List[UserCompactModel | UserItemModel]
    perPage: int
    total: int


class RolesResponseModel(BaseModel):
    items: List[RoleModel]
    perPage: int
    total: int


class ActivityItemModel(BaseModel):
    id: int
    user_id: int
    action: Optional[str] = Field(..., max_length=100)
    subject: Optional[Dict]
    tag: Optional[str] = Field(..., max_length=100)
    created_at: str


class ActivitiesResponseModel(BaseModel):
    items: List[ActivityItemModel]
    perPage: int
    total: int


class QueryItemModel(BaseModel):
    id: int
    name: Optional[str]
    data: Optional[Dict]
    query_type: str


class QueriesResponseModel(BaseModel):
    queries: List[QueryItemModel]


class AppConfigItemModel(BaseModel):
    id: int
    config: Dict
    created_at: str
    user: Optional[UserItemModel] = {}


class AppConfigsResponseModel(BaseModel):
    items: List[AppConfigItemModel]
    perPage: int
    total: int
