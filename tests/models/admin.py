from typing import Any, ForwardRef, Optional, Union
from pydantic import BaseModel, Field
from tests.models.user import UserCompactModel, RoleModel, UserItemModel
from tests.models.common import BaseResponseModel, StrictModel, BaseResponseDataModel

## PYDANTIC MODELS ##


class LocationTypeModel(BaseModel):
    id: int
    title: str
    description: Optional[str] = None


class AdminLevelModel(BaseModel):
    id: int
    code: int
    description: Optional[str] = None


class CountryModel(BaseModel):
    id: int
    title: str
    title_tr: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class LocationItemModel(BaseModel):
    id: int
    title: Optional[str] = None
    title_ar: Optional[str] = None
    description: Optional[str] = None
    location_type: Optional[LocationTypeModel] = None
    admin_level: Optional[AdminLevelModel] = None
    latlng: Optional[dict[str, float]] = Field(default=None, alias="latlng")
    postal_code: Optional[str] = None
    country: Optional[CountryModel] = None
    parent: Optional[ForwardRef("LocationItemModel")] = None  # type: ignore
    tags: list[str] = Field(default_factory=list)
    lat: Optional[float] = None
    lng: Optional[float] = None
    full_location: Optional[str] = None
    full_string: Optional[str] = None
    updated_at: Optional[str] = None


# Because parent field self-references, we need to handle forward refs
LocationItemModel.model_rebuild()


class LocationResponseDataModel(BaseResponseDataModel):
    items: list[LocationItemModel] = Field(default_factory=list)
    perPage: int
    total: int


class LocationResponseModel(BaseResponseModel):
    data: LocationResponseDataModel


class LocationRequestModel(BaseModel):
    item: dict


class ActorItemMinModel(StrictModel):
    id: int
    type_: Optional[str] = Field(alias="type", default=None)
    title: str = Field(default=None, max_length=255)
    name: Optional[str] = Field(default=None, max_length=255)
    assigned_to: Optional["UserCompactModel"] = None
    first_peer_reviewer: Optional["UserCompactModel"] = None
    status: Optional[str] = Field(default=None, max_length=255)
    u_status: Optional[str] = Field(alias="_status", default=None)  # since status field is optional
    roles: Optional[list["RoleModel"]] = Field(default_factory=list)


class SourcesJSONModel(BaseModel):
    id: int
    title: Optional[str] = None


class LabelsJSONModel(BaseModel):
    id: int
    title: Optional[str] = None


class VerLabelsJSONModel(BaseModel):
    id: int
    title: Optional[str] = None


class ActorItemMode2Model(StrictModel):
    class_: str = Field(default="Actor", alias="class")
    id: int
    type_: Optional[str] = Field(default=None, alias="type", max_length=255)
    # originid: Optional[str] = Field(None, max_length=255)
    name: Optional[str] = Field(default=None, max_length=255)
    # description: Optional[str]
    comments: Optional[str] = None
    # sources: Optional[list["SourcesJSONModel"]]
    # publish_date: Optional[str]
    # documentation_date: Optional[str]
    status: Optional[str] = Field(default=None, max_length=255)


class EthnographyModel(BaseModel):
    id: int
    title: str
    title_tr: Optional[str] = None
    created_at: str
    updated_at: str


class EventTypeModel(BaseModel):
    id: int
    title: Optional[str] = None
    title_ar: Optional[str] = None
    for_actor: bool = False
    for_bulletin: bool = False
    comments: Optional[str] = None
    updated_at: str


class EventModel(BaseModel):
    id: int
    title: Optional[str] = None
    title_ar: Optional[str] = None
    comments: Optional[str] = None
    comments_ar: Optional[str] = None
    location: Optional[LocationItemModel] = None
    eventtype: Optional[EventTypeModel] = None
    from_date: str
    to_date: str
    estimated: Optional[bool] = None
    updated_at: str


class MediaModel(BaseModel):
    id: int
    title: Optional[str] = None
    title_ar: Optional[str] = None
    fileType: Optional[str] = Field(default=None, alias="media_file_type")
    filename: Optional[str] = Field(default=None, alias="media_file")
    etag: Optional[str] = None
    time: Optional[float] = None
    duration: Optional[str] = None
    main: bool = False
    updated_at: Optional[str] = None


class DialectModel(BaseModel):
    id: int
    title: str
    title_tr: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SourceModel(BaseModel):
    id: int
    title: Optional[str] = None
    etl_id: Optional[str] = None
    parent: Optional[SourcesJSONModel] = None
    comments: Optional[str] = None
    updated_at: Optional[str] = None


class LabelModel(BaseModel):
    id: int
    title: Optional[str] = None
    title_ar: Optional[str] = None
    comments: Optional[str] = None
    comments_ar: Optional[str] = None
    order: Optional[int] = None
    verified: Optional[bool] = Field(default=False)
    for_bulletin: Optional[bool] = Field(default=False)
    for_actor: Optional[bool] = Field(default=False)
    for_incident: Optional[bool] = Field(default=False)
    for_offline: Optional[bool] = Field(default=False)
    parent: Optional[LabelsJSONModel] = None
    updated_at: Optional[str] = None


class ActorProfileModel(BaseModel):
    id: int
    mode: int = Field(default=1)
    description: Optional[str] = None
    source_link: Optional[str] = None
    publish_date: Optional[str] = None
    documentation_date: Optional[str] = None
    actor_id: int
    sources: Optional[list[SourceModel]] = Field(default_factory=list)
    labels: Optional[list[LabelModel]] = Field(default_factory=list)
    ver_labels: Optional[list[LabelModel]] = Field(default_factory=list)


class ActorItemMode3Model(BaseModel):
    class_: str = Field(alias="class")  # nolimit
    id: int
    originid: Optional[str] = Field(default=None, max_length=255)
    name: Optional[str] = Field(default=None, max_length=255)
    name_ar: Optional[str] = Field(default=None, max_length=255)
    # description: Optional[str]  # nolimit
    nickname: Optional[str] = Field(default=None, max_length=255)
    nickname_ar: Optional[str] = Field(default=None, max_length=255)
    first_name: Optional[str] = Field(default=None, max_length=255)
    first_name_ar: Optional[str] = Field(default=None, max_length=255)
    middle_name: Optional[str] = Field(default=None, max_length=255)
    middle_name_ar: Optional[str] = Field(default=None, max_length=255)
    last_name: Optional[str] = Field(default=None, max_length=255)
    last_name_ar: Optional[str] = Field(default=None, max_length=255)
    mother_name: Optional[str] = Field(default=None, max_length=255)
    mother_name_ar: Optional[str] = Field(default=None, max_length=255)
    father_name: Optional[str] = Field(default=None, max_length=255)
    father_name_ar: Optional[str] = Field(default=None, max_length=255)
    sex: Optional[str] = Field(default=None, max_length=255)
    u_sex: Optional[str] = Field(alias="_sex", default=None)  # nolimit
    age: Optional[str] = Field(default=None, max_length=255)
    u_age: Optional[str] = Field(alias="_age", default=None)  # nolimit
    civilian: Optional[str] = Field(default=None, max_length=255)
    u_civilian: Optional[str] = Field(alias="_civilian", default=None)  # nolimit
    type_: Optional[str] = Field(alias="type", max_length=255, default=None)
    u_type: Optional[str] = Field(alias="_type", default=None)
    occupation: Optional[str] = Field(default=None, max_length=255)
    occupation_ar: Optional[str] = Field(default=None, max_length=255)
    position: Optional[str] = Field(default=None, max_length=255)
    position_ar: Optional[str] = Field(default=None, max_length=255)
    family_status: Optional[str] = Field(default=None, max_length=255)
    no_children: Optional[int] = Field(default=None)
    ethnographies: list[EthnographyModel] = Field(default_factory=list)
    nationalities: list[CountryModel] = Field(default_factory=list)
    dialects: Optional[list[DialectModel]] = Field(default_factory=list)
    id_number: Optional[str] = Field(max_length=255, default=None)
    assigned_to: Optional["UserCompactModel"] = None
    first_peer_reviewer: Optional["UserCompactModel"] = None
    source_link: Optional[str] = Field(default=None, max_length=255)
    source_link_type: Optional[bool] = False
    comments: Optional[str] = None
    events: Optional[list[EventModel]] = Field(default_factory=list)
    medias: Optional[list[MediaModel]] = Field(default_factory=list)
    actor_relations: Optional[list] = Field(default_factory=list)  # Lazy load in mode3
    bulletin_relations: Optional[list] = Field(default_factory=list)  # Lazy load in mode3
    incident_relations: Optional[list] = Field(default_factory=list)  # Lazy load in mode3
    birth_place: Optional[LocationItemModel] = None
    residence_place: Optional[LocationItemModel] = None
    origin_place: Optional[LocationItemModel] = None
    birth_date: Optional[str] = None
    status: Optional[str] = Field(default=None, max_length=255)
    review: Optional[str] = None
    review_action: Optional[str] = None
    updated_at: Optional[str] = None
    roles: list[RoleModel] = Field(default_factory=list)
    actor_profiles: list[ActorProfileModel] = Field(default_factory=list)


class ActorCompactModel(StrictModel):
    id: int
    name: Optional[str] = Field(default=None, max_length=255)


class LocationsJSONModel(BaseModel):
    id: int
    title: Optional[str] = None
    full_string: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


class BulletinCompactModel(StrictModel):
    id: int
    title: str = Field(default=None, max_length=255)
    title_ar: Optional[str] = Field(default=None, max_length=255)
    sjac_title: Optional[str] = Field(default=None, max_length=255)
    sjac_title_ar: Optional[str] = Field(default=None, max_length=255)
    originid: Optional[str] = None
    locations: Optional[list[LocationsJSONModel]] = Field(default_factory=list)
    sources: Optional[list[SourcesJSONModel]] = Field(default_factory=list)
    description: Optional[str] = None
    source_link: Optional[str] = Field(default=None, max_length=255)
    source_link_type: Optional[bool] = False
    publish_date: str
    documentation_date: str
    comments: Optional[str] = None


class AtobModel(BaseModel):
    bulletin: BulletinCompactModel
    actor: ActorCompactModel
    related_as: Optional[list[int]] = Field(default_factory=list)
    probability: Optional[int] = None
    comment: Optional[str] = None
    user_id: Optional[int] = None


class AtoaModel(BaseModel):
    actor: ActorCompactModel
    related_as: Optional[int] = None
    probability: Optional[int] = None
    comment: Optional[str] = None
    user_id: Optional[int] = None


class IncidentItemCompactModel(BaseModel):
    id: int
    title: str = Field(default=None, max_length=255)
    description: Optional[str] = None


class ItoaModel(BaseModel):
    actor: ActorCompactModel
    incident: IncidentItemCompactModel
    related_as: Optional[list[int]] = Field(default_factory=list)
    probability: Optional[int] = None
    comment: Optional[str] = None
    user_id: Optional[int] = None


class ActorItemMode3PlusModel(ActorItemMode3Model):
    bulletin_relations: Optional[list[AtobModel]] = Field(default_factory=list)
    actor_relations: Optional[list[AtoaModel]] = Field(default_factory=list)
    incident_relations: Optional[list[ItoaModel]] = Field(default_factory=list)


class ActorItemRestrictedModel(StrictModel):
    id: int
    restricted: bool = True


class ActorsResponseDataModel(BaseResponseDataModel):
    items: list[
        Union[ActorItemMinModel, ActorItemMode2Model, ActorItemMode3Model, ActorItemMode3PlusModel]
    ]
    perPage: int
    total: int


class ActorsResponseModel(BaseResponseModel):
    data: ActorsResponseDataModel


class ActorRequestModel(BaseModel):
    item: dict


class BulletinItemMinModel(BaseModel):
    id: int
    type_: Optional[str] = Field(default=None, alias="type")
    title: str = Field(default=None, max_length=255)
    name: Optional[str] = Field(default=None, max_length=255)
    assigned_to: Optional["UserCompactModel"] = None
    first_peer_reviewer: Optional["UserCompactModel"] = None
    status: Optional[str] = Field(default=None, max_length=255)
    u_status: Optional[str] = Field(alias="_status", default=None)
    roles: Optional[list["RoleModel"]] = Field(default_factory=list)


class LocationItemCompactModel(BaseModel):
    id: int
    title: Optional[str] = None
    full_string: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


class BulletinItemMode2Model(BaseModel):
    class_: str = Field(default="Bulletin", alias="class")
    id: int
    title: str
    title_ar: Optional[str] = None
    sjac_title: Optional[str] = None
    sjac_title_ar: Optional[str] = None
    originid: Optional[str] = None
    locations: list[LocationItemCompactModel] = Field(default_factory=list)
    sources: list[SourcesJSONModel] = Field(default_factory=list)
    description: Optional[str] = None
    comments: Optional[str] = None
    source_link: Optional[str] = None
    publish_date: Optional[str] = None
    documentation_date: Optional[str] = None


class GeoLocationTypeItemModel(BaseModel):
    id: int
    title: str
    title_tr: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class GeoLocationItemModel(BaseModel):
    id: int
    title: Optional[str] = None
    type_id: Optional[int] = None
    geotype: Optional[GeoLocationTypeItemModel] = None
    main: Optional[bool] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    comment: Optional[str] = None
    updated_at: Optional[str] = None


class BulletinItemMode3Model(BaseModel):
    class_: str = Field(alias="class")
    id: int
    title: str
    title_ar: Optional[str] = None
    sjac_title: Optional[str] = None
    sjac_title_ar: Optional[str] = None
    originid: Optional[str] = None
    assigned_to: Optional[UserCompactModel] = None
    first_peer_reviewer: Optional[UserCompactModel] = None
    locations: Optional[list[LocationItemCompactModel]] = Field(default_factory=list)
    geoLocations: list[GeoLocationItemModel] = Field(default_factory=list)
    labels: Optional[list[LabelsJSONModel]] = Field(default_factory=list)
    verLabels: Optional[list[LabelsJSONModel]] = Field(default_factory=list)
    sources: Optional[list[SourcesJSONModel]] = Field(default_factory=list)
    events: Optional[list[EventModel]] = Field(default_factory=list)
    medias: Optional[list[MediaModel]] = Field(default_factory=list)
    bulletin_relations: Optional[list[dict]] = Field(default_factory=list)  # Lazy loading in mode 3
    actor_relations: Optional[list[dict]] = Field(default_factory=list)  # Lazy loading in mode 3
    incident_relations: Optional[list[dict]] = Field(default_factory=list)  # Lazy loading in mode 3
    description: Optional[str] = None
    comments: Optional[str] = None
    source_link: Optional[str] = None
    source_link_type: Optional[bool] = None
    ref: Optional[list[str]] = Field(default_factory=list)
    publish_date: Optional[str] = None
    documentation_date: Optional[str] = None
    status: Optional[str] = None
    review: Optional[str] = None
    review_action: Optional[str] = None
    updated_at: Optional[str] = None
    roles: list[RoleModel] = Field(default_factory=list)


class BtobModel(BaseModel):
    bulletin: BulletinCompactModel
    related_as: Optional[list[int]] = Field(default_factory=list)
    probability: Optional[int] = None
    comment: Optional[str] = None
    user_id: Optional[int] = None


class ItobModel(BaseModel):
    incident: IncidentItemCompactModel
    bulletin: BulletinCompactModel
    related_as: Optional[int] = None
    probability: Optional[int] = None
    comment: Optional[str] = None
    user_id: Optional[int] = None


class BulletinItemMode3PlusModel(BulletinItemMode3Model):
    bulletin_relations: Optional[list[BtobModel]] = Field(default_factory=list)
    actor_relations: Optional[list[AtobModel]] = Field(default_factory=list)
    incident_relations: Optional[list[ItobModel]] = Field(default_factory=list)


class BulletinItemRestrictedModel(StrictModel):
    id: int
    restricted: bool = True


class BulletinsResponseDataModel(BaseResponseDataModel):
    items: list[
        Union[
            BulletinItemMinModel,
            BulletinItemMode2Model,
            BulletinItemMode3Model,
            BulletinItemMode3PlusModel,
        ]
    ]
    perPage: int
    total: int


class BulletinsResponseModel(BaseResponseModel):
    data: BulletinsResponseDataModel


class BulletinRequestModel(BaseModel):
    item: dict


class IncidentItemRestrictedModel(StrictModel):
    id: int
    restricted: bool = True


class IncidentItemMinModel(StrictModel):
    id: int
    title: str = Field(default=None, max_length=255)
    type_: Optional[str] = Field(default=None, alias="type")
    name: Optional[str] = Field(default=None, max_length=255)
    assigned_to: Optional["UserCompactModel"] = None
    first_peer_reviewer: Optional["UserCompactModel"] = None
    status: Optional[str] = Field(default=None, max_length=255)
    u_status: Optional[str] = Field(alias="_status", default=None)  # since status field is optional
    roles: Optional[list["RoleModel"]] = Field(default_factory=list)


class LocationItemMinModel(BaseModel):
    id: int
    location_type: Optional[str | LocationTypeModel] = ""
    full_string: Optional[str] = None


class IncidentItemMode2Model(BaseModel):
    class_: str = Field(default="Incident", alias="class")
    id: int
    title: Optional[str] = None
    description: Optional[str] = None
    labels: list[LabelsJSONModel] = Field(default_factory=list)
    locations: list[LocationItemMinModel] = Field(default_factory=list)
    comments: Optional[str] = None
    status: Optional[str] = None


class PotentialViolationJSONModel(BaseModel):
    id: int
    title: Optional[str] = None


class ClaimedViolationJSONModel(BaseModel):
    id: int
    title: Optional[str] = None


class IncidentItemMode3Model(StrictModel):
    class_: str = Field(alias="class")
    id: int
    title: Optional[str] = None
    title_ar: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[UserCompactModel] = None
    first_peer_reviewer: Optional[UserCompactModel] = None
    labels: list[LabelsJSONModel] = Field(default_factory=list)
    locations: list[LocationItemCompactModel] = Field(default_factory=list)
    potential_violations: list[PotentialViolationJSONModel] = Field(default_factory=list)
    claimed_violations: list[ClaimedViolationJSONModel] = Field(default_factory=list)
    events: list[EventModel] = Field(default_factory=list)
    actor_relations: list[dict] = Field(default_factory=list)  # Lazy load in mode 3
    bulletin_relations: list[dict] = Field(default_factory=list)  # Lazy load in mode 3
    incident_relations: list[dict] = Field(default_factory=list)  # Lazy load in mode 3
    comments: Optional[str] = None
    status: Optional[str] = None
    review: Optional[str] = None
    review_action: Optional[str] = None
    updated_at: str
    roles: list[RoleModel] = Field(default_factory=list)


class ItoiModel(BaseModel):
    incident: IncidentItemCompactModel
    related_as: Optional[int] = None
    probability: Optional[int] = None
    comment: Optional[str] = None
    user_id: Optional[int] = None


class IncidentItemMode3PlusModel(IncidentItemMode3Model):
    actor_relations: list[ItoaModel] = Field(default_factory=list)
    bulletin_relations: list[ItobModel] = Field(default_factory=list)
    incident_relations: list[ItoiModel] = Field(default_factory=list)


class IncidentsResponseDataModel(BaseResponseDataModel):
    items: list[
        Union[
            IncidentItemMinModel,
            IncidentItemMode2Model,
            IncidentItemMode3Model,
            IncidentItemMode3PlusModel,
        ]
    ]
    perPage: int
    total: int


class IncidentsResponseModel(BaseResponseModel):
    data: IncidentsResponseDataModel


class IncidentRequestModel(BaseModel):
    item: dict


class LabelMode2Model(BaseModel):
    id: int
    title: Optional[str] = None


class LabelModel(LabelMode2Model):
    title_ar: Optional[str] = None
    comments: Optional[str] = None
    comments_ar: Optional[str] = None
    order: Optional[int] = None
    verified: Optional[bool] = Field(default=False)
    for_bulletin: Optional[bool] = Field(default=False)
    for_actor: Optional[bool] = Field(default=False)
    for_incident: Optional[bool] = Field(default=False)
    for_offline: Optional[bool] = Field(default=False)
    parent: Optional[LabelMode2Model] = None
    updated_at: Optional[str] = None


class LabelsResponseDataModel(BaseResponseDataModel):
    items: list[LabelMode2Model | LabelModel]
    perPage: int
    total: int


class LabelsResponseModel(BaseResponseModel):
    data: LabelsResponseDataModel


class EventTypeItemModel(BaseModel):
    id: int
    title: Optional[str] = None
    title_ar: Optional[str] = None
    for_actor: Optional[bool] = Field(default=False)
    for_bulletin: Optional[bool] = Field(default=False)
    comments: Optional[str] = None
    updated_at: Optional[str] = None


class EventtypesResponseDataModel(BaseResponseDataModel):
    items: list[EventTypeItemModel]
    perPage: int
    total: int


class EventtypesResponseModel(BaseResponseModel):
    data: EventtypesResponseDataModel


class PotentialViolationItemModel(BaseModel):
    id: int
    title: Optional[str] = None


class PotentialViolationsResponseDataModel(BaseResponseDataModel):
    items: list[PotentialViolationItemModel]
    perPage: int
    total: int


class PotentialViolationsResponseModel(BaseResponseModel):
    data: PotentialViolationsResponseDataModel


class ClaimedViolationItemModel(BaseModel):
    id: int
    title: Optional[str] = None


class ClaimedViolationsResponseDataModel(BaseResponseDataModel):
    items: list[ClaimedViolationItemModel]
    perPage: int
    total: int


class ClaimedViolationsResponseModel(BaseResponseModel):
    data: ClaimedViolationsResponseDataModel


class SourceItemModel(BaseModel):
    id: int
    etl_id: Optional[str] = None
    title: Optional[str] = None
    parent: Optional[SourcesJSONModel] = None
    comments: Optional[str] = None
    updated_at: Optional[str] = None


class SourcesResponseDataModel(BaseResponseDataModel):
    items: list[SourceItemModel]
    perPage: int
    total: int


class SourcesResponseModel(BaseResponseModel):
    data: SourcesResponseDataModel


class LocationAdminLevelItemModel(BaseModel):
    id: int
    code: int
    title: Optional[str] = None


class LocationAdminLevelsResponseDataModel(BaseResponseDataModel):
    items: list[LocationAdminLevelItemModel]
    perPage: int
    total: int


class LocationAdminLevelsResponseModel(BaseResponseModel):
    data: LocationAdminLevelsResponseDataModel


class LocationTypesResponseDataModel(BaseResponseDataModel):
    items: list[LocationTypeModel]
    perPage: int
    total: int


class LocationTypesResponseModel(BaseResponseModel):
    data: LocationTypesResponseDataModel


class CountriesResponseDataModel(BaseResponseDataModel):
    items: list[CountryModel]
    perPage: int
    total: int


class CountriesResponseModel(BaseResponseModel):
    data: CountriesResponseDataModel


class EthnographiesResponseDataModel(BaseResponseDataModel):
    items: list[EthnographyModel]
    perPage: int
    total: int


class EthnographiesResponseModel(BaseResponseModel):
    data: EthnographiesResponseDataModel


class AtoaInfoItemModel(BaseModel):
    id: int
    title: str
    reverse_title: str
    title_tr: Optional[str] = None
    reverse_title_tr: Optional[str] = None


class AtoaInfosResponseDataModel(BaseResponseDataModel):
    items: list[AtoaInfoItemModel]
    perPage: int
    total: int


class AtoaInfosResponseModel(BaseResponseModel):
    data: AtoaInfosResponseDataModel


class AtobInfoItemModel(BaseModel):
    id: int
    title: str
    reverse_title: str
    title_tr: Optional[str] = None
    reverse_title_tr: Optional[str] = None


class AtobInfosResponseDataModel(BaseResponseDataModel):
    items: list[AtobInfoItemModel]
    perPage: int
    total: int


class AtobInfosResponseModel(BaseResponseModel):
    data: AtobInfosResponseDataModel


class BtobInfoItemModel(BaseModel):
    id: int
    title: str
    reverse_title: str
    title_tr: Optional[str] = None
    reverse_title_tr: Optional[str] = None


class BtobInfosResponseDataModel(BaseResponseDataModel):
    items: list[BtobInfoItemModel]
    perPage: int
    total: int


class BtobInfosResponseModel(BaseResponseModel):
    data: BtobInfosResponseDataModel


class ItoaInfoItemModel(BaseModel):
    id: int
    title: str
    reverse_title: str
    title_tr: Optional[str] = None
    reverse_title_tr: Optional[str] = None


class ItoaInfosResponseDataModel(BaseResponseDataModel):
    items: list[ItoaInfoItemModel]
    perPage: int
    total: int


class ItoaInfosResponseModel(BaseResponseModel):
    data: ItoaInfosResponseDataModel


class ItobInfoItemModel(BaseModel):
    id: int
    title: str
    reverse_title: str
    title_tr: Optional[str] = None
    reverse_title_tr: Optional[str] = None


class ItobInfosResponseDataModel(BaseResponseDataModel):
    items: list[ItobInfoItemModel]
    perPage: int
    total: int


class ItobInfosResponseModel(BaseResponseModel):
    data: ItobInfosResponseDataModel


class ItoiInfoItemModel(BaseModel):
    id: int
    title: str
    reverse_title: str
    title_tr: Optional[str] = None
    reverse_title_tr: Optional[str] = None


class ItoiInfosResponseDataModel(BaseResponseDataModel):
    items: list[ItoiInfoItemModel]
    perPage: int
    total: int


class ItoiInfosResponseModel(BaseResponseModel):
    data: ItoiInfosResponseDataModel


class MediaCategoryItemModel(BaseModel):
    id: int
    title: str
    title_tr: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MediaCategoriesResponseDataModel(BaseResponseDataModel):
    items: list[MediaCategoryItemModel]
    perPage: int
    total: int


class MediaCategoriesResponseModel(BaseResponseModel):
    data: MediaCategoriesResponseDataModel


class GeoLocationTypesResponseDataModel(BaseResponseDataModel):
    items: list[MediaCategoryItemModel]
    perPage: int
    total: int


class GeoLocationTypesResponseModel(BaseResponseModel):
    data: GeoLocationTypesResponseDataModel


class HistoryHelperItemModel(BaseModel):
    id: int
    data: Optional[dict] = Field(default_factory=dict)
    created_at: str
    updated_at: Optional[str] = None
    user: Optional[UserCompactModel] = None


class HistoryHelpersResponseDataModel(BaseResponseDataModel):
    items: list[HistoryHelperItemModel]
    perPage: int
    total: int


class HistoryHelpersResponseModel(BaseResponseModel):
    data: HistoryHelpersResponseDataModel


class UsersResponseDataModel(BaseResponseDataModel):
    items: list[UserCompactModel | UserItemModel]
    perPage: int
    total: int


class UsersResponseModel(BaseResponseModel):
    data: UsersResponseDataModel


class RolesResponseDataModel(BaseResponseDataModel):
    items: list[RoleModel]
    perPage: int
    total: int


class RolesResponseModel(BaseResponseModel):
    data: RolesResponseDataModel


class ActivityItemModel(BaseModel):
    id: int
    user_id: int
    action: Optional[str] = Field(max_length=100, default=None)
    model: Optional[str] = Field(max_length=100, default=None)
    subject: Optional[dict] = Field(default_factory=dict)
    details: Optional[str] = None
    created_at: str


class ActivitiesResponseDataModel(BaseResponseDataModel):
    items: list[ActivityItemModel]
    perPage: int
    total: int


class ActivitiesResponseModel(BaseResponseModel):
    data: ActivitiesResponseDataModel


class QueryItemModel(BaseModel):
    id: int
    name: Optional[str] = None
    data: Optional[dict] = Field(default_factory=dict)
    query_type: str


class QueriesResponseModel(BaseModel):
    queries: list[QueryItemModel]


class AppConfigItemModel(BaseModel):
    id: int
    config: dict
    created_at: str
    user: Optional[UserItemModel] = None


class AppConfigsResponseDataModel(BaseResponseDataModel):
    items: list[AppConfigItemModel]
    perPage: int
    total: int


class AppConfigsResponseModel(BaseResponseModel):
    data: AppConfigsResponseDataModel


class UserSessionItemModel(BaseModel):
    id: int
    user_id: int
    details: Optional[dict[str, Any]] = Field(default_factory=dict)
    last_active: Optional[str] = None
    expires_at: Optional[str] = None
    ip_address: str
    meta: Optional[dict] = Field(default_factory=dict)
    is_active: bool
    created_at: str
    updated_at: str


class UserSessionsResponseDataModel(BaseResponseDataModel):
    items: list[UserSessionItemModel]
    more: bool


class UserSessionsResponseModel(BaseResponseModel):
    data: UserSessionsResponseDataModel
