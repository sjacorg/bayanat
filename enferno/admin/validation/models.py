from enum import Enum
from pydantic import BaseModel, validator, Field, root_validator, constr
from typing import Dict, Optional, List, Any
from urllib.parse import urlparse
from pydantic import BaseModel
from typing import List, Optional
from dateutil.parser import parse

from enferno.admin.constants import Constants
from enferno.admin.validation.util import one_must_exist, sanitize
from enferno.utils.typing import typ as t

DEFAULT_STRING_FIELD = Field(None, max_length=255)


class BaseValidationModel(BaseModel):
    """Base class for all validation models."""

    class Config:
        anystr_strip_whitespace = True


class StrictValidationModel(BaseValidationModel):
    """Base class that forbids extra fields in the model."""

    class Config:
        extra = "forbid"


class PartialUserModel(BaseValidationModel):
    id: int


class PartialRoleModel(BaseValidationModel):
    id: int
    color: Optional[str]
    description: Optional[str] = sanitize()
    name: Optional[str]


class PartialLocationModel(BaseValidationModel):
    id: int


class PartialGeoLocationTypeModel(BaseValidationModel):
    id: Optional[int]


class PartialSourceModel(BaseValidationModel):
    id: int


class PartialLabelModel(BaseValidationModel):
    id: int


class PartialGeoLocationModel(BaseValidationModel):
    id: Optional[int]
    title: constr(min_length=1)  # type: ignore
    geotype: Optional[PartialGeoLocationTypeModel]
    main: Optional[bool]
    lng: float
    lat: float
    comment: Optional[str]


class PartialEventLocationModel(BaseValidationModel):
    id: Optional[int]


class PartialEventtypeModel(BaseValidationModel):
    id: Optional[str]


class PartialManyRelationModel(BaseValidationModel):
    probability: Optional[int]
    comment: Optional[str]
    related_as: Optional[List[int]] = Field(default_factory=list)


class PartialSingleRelationModel(BaseValidationModel):
    probability: Optional[int]
    comment: Optional[str]
    related_as: Optional[int]


class PartialBulletinRelationModel(BaseValidationModel):
    id: int


class PartialActorRelationModel(BaseValidationModel):
    id: int


class PartialIncidentRelationModel(BaseValidationModel):
    id: int


class PartialAtoaModel(PartialSingleRelationModel):
    actor: PartialActorRelationModel


class PartialItobModel(PartialSingleRelationModel):
    bulletin: PartialBulletinRelationModel


class PartialBtoiModel(PartialSingleRelationModel):
    incident: PartialIncidentRelationModel


class PartialItoiModel(PartialSingleRelationModel):
    incident: PartialIncidentRelationModel


class PartialAtobModel(PartialManyRelationModel):
    bulletin: PartialBulletinRelationModel


class PartialBtoaModel(PartialManyRelationModel):
    actor: PartialActorRelationModel


class PartialBtobModel(PartialManyRelationModel):
    bulletin: PartialBulletinRelationModel


class PartialItoaModel(PartialManyRelationModel):
    actor: PartialActorRelationModel


class PartialAtoiModel(PartialManyRelationModel):
    incident: PartialIncidentRelationModel


class PartialEventModel(BaseValidationModel):
    id: Optional[int]
    title: Optional[str]
    title_ar: Optional[str]
    comments: Optional[str]
    comments_ar: Optional[str]
    location: Optional[PartialEventLocationModel]
    eventtype: Optional[PartialEventtypeModel]
    from_date: Optional[str]
    to_date: Optional[str]
    estimated: Optional[bool]

    @validator("from_date", "to_date", pre=True, each_item=True)
    def validate_date(cls, v):
        """
        Validates the date fields.

        Returns:
            str: The validated date value.

        Raises:
            ValueError: If the date is not a valid date.
        """
        if v:
            try:
                parse(v)
            except ValueError:
                raise ValueError(f"Invalid date format: {v}")
        return v

    @validator("to_date", pre=False)
    def validate_to_date(cls, v, values):
        """
        Validates the to_date field.

        Returns:
            str: The validated to_date value.

        Raises:
            ValueError: If the to_date is before the from_date.
        """
        if values.get("from_date") and v:
            from_date = parse(values["from_date"])
            to_date = parse(v)
            if to_date < from_date:
                raise ValueError("to_date must be after from_date")
        return v


class PartialMediaCategoryModel(BaseValidationModel):
    id: Optional[int]


class PartialMediaModel(BaseValidationModel):
    id: Optional[int]
    main: Optional[bool]
    title: Optional[str]
    title_ar: Optional[str]
    fileType: Optional[str]
    filename: Optional[str]
    etag: Optional[str]
    time: Optional[str]
    category: Optional[PartialMediaCategoryModel]


class BulletinValidationModel(StrictValidationModel):
    originid: Optional[str]
    title: constr(min_length=1)  # type: ignore
    sjac_title: Optional[str]
    assigned_to: Optional[PartialUserModel]
    first_peer_reviewer: Optional[PartialUserModel]
    description: Optional[str] = sanitize()
    comments: constr(min_length=1)  # type: ignore
    source_link: constr(min_length=1)  # type: ignore
    source_link_type: Optional[bool]
    ref: Optional[List[str]] = []
    locations: List[PartialLocationModel] = Field(default_factory=list)
    geoLocations: List[PartialGeoLocationModel] = Field(default_factory=list)
    sources: List[PartialSourceModel] = Field(default_factory=list)
    labels: List[PartialLabelModel] = Field(default_factory=list)
    verLabels: List[PartialLabelModel] = Field(default_factory=list)
    events: List[PartialEventModel] = Field(default_factory=list)
    medias: List[PartialMediaModel] = Field(default_factory=list)
    bulletin_relations: List[PartialBtobModel] = Field(default_factory=list)
    actor_relations: List[PartialBtoaModel] = Field(default_factory=list)
    incident_relations: List[PartialBtoiModel] = Field(default_factory=list)

    publish_date: Optional[str]
    documentation_date: Optional[str]
    status: Optional[str]

    roles: List[PartialRoleModel] = Field(default_factory=list)

    id: Optional[int]
    review: Optional[str] = sanitize()
    review_action: Optional[str]
    sjac_title_ar: Optional[str]
    title_ar: Optional[str]
    updated_at: Optional[str]
    class_: Optional[str] = Field(None, alias="class")

    @validator("source_link", pre=True)
    def validate_source_link(cls: t, v: str) -> str:
        """
        Validates the source_link field.

        Args:
            - v: The value of the source_link field.

        Raises:
            - ValueError: If the source_link is not a valid URL or 'NA'.

        Returns:
            - The validated source_link value.
        """
        if v and v != "NA":
            parsed_url = urlparse(v)
            if not all([parsed_url.scheme, parsed_url.netloc]):
                raise ValueError("source_link must be a valid URL or 'NA'")
        return v

    @validator("publish_date", "documentation_date", pre=True, each_item=True)
    def validate_date(cls, v):
        """
        Validates the date fields.

        Returns:
            str: The validated date value.

        Raises:
            ValueError: If the date is not a valid date.
        """
        if v:
            try:
                parse(v)
            except ValueError:
                raise ValueError(f"Invalid date format: {v}")
        return v


class BulletinRequestModel(BaseValidationModel):
    item: BulletinValidationModel


class PartialPotentialViolationModel(BaseValidationModel):
    id: int


class PartialClaimedViolationModel(BaseValidationModel):
    id: int


class IncidentValidationModel(StrictValidationModel):
    title: constr(min_length=1)  # type: ignore
    title_ar: Optional[str]
    description: Optional[str] = sanitize()
    labels: List[PartialLabelModel] = Field(default_factory=list)
    locations: List[PartialLocationModel] = Field(default_factory=list)
    potential_violations: List[PartialPotentialViolationModel] = Field(default_factory=list)
    claimed_violations: List[PartialClaimedViolationModel] = Field(default_factory=list)
    events: List[PartialEventModel] = Field(default_factory=list)
    check_ar: Optional[bool]
    check_ir: Optional[Any]
    check_br: Optional[Any]
    actor_relations: List[PartialItoaModel] = Field(default_factory=list)
    bulletin_relations: List[PartialItobModel] = Field(default_factory=list)
    incident_relations: List[PartialItoiModel] = Field(default_factory=list)
    comments: constr(min_length=1)  # type: ignore
    status: Optional[str]

    # Below fields are sent by the front-end, dismissed by `from_json`
    documentation_date: Optional[str]
    publish_date: Optional[str]
    assigned_to: Optional[PartialUserModel]
    first_peer_reviewer: Optional[PartialUserModel]
    id: Optional[int]
    class_: Optional[str] = Field(alias="class")
    review: Optional[str] = sanitize()
    review_action: Optional[str]
    updated_at: Optional[str]
    roles: List[PartialRoleModel] = Field(default_factory=list)

    @validator("actor_relations", pre=False, always=False)
    def check_actor_relations(cls: t, v: list, values: dict, **kwargs) -> list:
        """
        Check the validity of actor_relations field.

        This validator checks if the actor_relations field is provided without the check_ar field.
        If the actor_relations field is empty, it returns an empty list.
        If the actor_relations field is not empty and the check_ar field is not present in the values dictionary, it raises a ValueError.

        Args:
        - v: The value of the actor_relations field.
        - values: The values dictionary containing the other fields up to this validation call.
        - kwargs: Additional keyword arguments.

        Returns:
        - The value of the actor_relations field if it is valid.

        Raises:
        - ValueError: If the actor_relations field is provided without the check_ar field.

        """
        if not len(v):
            return []
        if (v and len(v)) and "check_ar" not in values:
            raise ValueError("actor_relations provided without check_ar")
        return v

    @validator("bulletin_relations", always=False, pre=False)
    def check_bulletin_relations(cls: t, v: list, values: dict, **kwargs) -> list:
        """
        Check the validity of bulletin_relations field.

        This validator checks if the bulletin_relations field is provided without the check_br field.
        If the bulletin_relations field is empty, it returns an empty list.
        If the bulletin_relations field is not empty and the check_br field is not present in the values dictionary, it raises a ValueError.

        Args:
        - v: The value of the bulletin_relations field.
        - values: The values dictionary containing the other fields up to this validation call.
        - kwargs: Additional keyword arguments.

        Returns:
        - The value of the bulletin_relations field if it is valid.

        Raises:
        - ValueError: If the bulletin_relations field is provided without the check_br field.

        """
        if not len(v):
            return []
        if (v and len(v)) and "check_br" not in values:
            raise ValueError("bulletin_relations provided without check_br")
        return v

    @validator("incident_relations", always=True)
    def check_incident_relations(cls: t, v: list, values: dict, **kwargs) -> list:
        """
        Check the validity of incident_relations field.

        This validator checks if the incident_relations field is provided without the check_ir field.
        If the incident_relations field is empty, it returns an empty list.
        If the incident_relations field is not empty and the check_ir field is not present in the values dictionary, it raises a ValueError.

        Args:
        - v: The value of the incident_relations field.
        - values: The values dictionary containing the other fields up to this validation call.
        - kwargs: Additional keyword arguments.

        Returns:
        - The value of the incident_relations field if it is valid.

        Raises:
        - ValueError: If the incident_relations field is provided without the check_ir field.
        """
        if not len(v):
            return []
        if (v and len(v)) and "check_ir" not in values:
            raise ValueError("incident_relations provided without check_ir")
        return v

    @validator("publish_date", "documentation_date", pre=True, each_item=True)
    def validate_date(cls, v):
        """
        Validates the date fields.

        Returns:
            str: The validated date value.

        Raises:
            ValueError: If the date is not a valid date.
        """
        if v:
            try:
                parse(v)
            except ValueError:
                raise ValueError(f"Invalid date format: {v}")
        return v


class IncidentRequestModel(BaseValidationModel):
    item: IncidentValidationModel


class PartialEthnographyModel(BaseValidationModel):
    id: int


class PartialNationalityModel(BaseValidationModel):
    id: int


class PartialDialectModel(BaseValidationModel):
    id: int


class PartialOriginPlaceModel(BaseValidationModel):
    id: Optional[int]


class OptsModel(BaseValidationModel):
    opts: Optional[str]
    details: Optional[str]

    @validator("opts", pre=True, each_item=False)
    def validate_opts(cls, v):
        """
        Validates the opts field.

        Returns:
            str: The validated opts value.

        Raises:
            ValueError: If the opts is not a valid value.
        """
        if v and len(v):
            if not v.lower() in [x.lower() for x in Constants.CLASSIC_OPTS]:
                raise ValueError("Invalid value for opts")
        return v


class SkinMarkingsModel(BaseValidationModel):
    opts: Optional[List[str]] = Field(default_factory=list)
    details: Optional[str]

    @validator("opts", pre=True, each_item=False)
    def validate_opts(cls, v):
        """
        Validates the opts field.

        Returns:
            str: The validated opts value.

        Raises:
            ValueError: If the opts is not a valid value.
        """
        if v and len(v):
            if not all(
                [opt.lower() in [x.lower() for x in Constants.SKIN_MARKINGS_OPTS] for opt in v]
            ):
                raise ValueError("Invalid value for skin_markings > opts")
        return v


class ReporterModel(BaseValidationModel):
    name: Optional[str]
    contact: Optional[str]
    relationship: Optional[str]


class PartialActorProfileModel(BaseValidationModel):
    id: Optional[int]
    actor_id: Optional[int]
    mode: int = 1
    originid: Optional[str]
    description: Optional[str] = sanitize()
    source_link: Optional[str] = DEFAULT_STRING_FIELD
    source_link_type: Optional[bool]
    publish_date: Optional[str]
    documentation_date: Optional[str]
    sources: List[PartialSourceModel] = Field(default_factory=list)
    labels: List[PartialLabelModel] = Field(default_factory=list)
    ver_labels: List[PartialLabelModel] = Field(default_factory=list)
    # Fields below are required if mode==3
    last_address: Optional[str]
    marriage_history: Optional[str]
    pregnant_at_disappearance: Optional[str]
    months_pregnant: Optional[int]
    missing_relatives: Optional[bool]
    saw_name: Optional[str]
    saw_address: Optional[str]
    saw_email: Optional[str]
    saw_phone: Optional[str]
    seen_in_detention: Optional[OptsModel]
    eye_color: Optional[str]
    injured: Optional[OptsModel]
    known_dead: Optional[OptsModel]
    death_details: Optional[str]
    personal_items: Optional[str]
    height: Optional[int]
    weight: Optional[int]
    physique: Optional[str]
    hair_loss: Optional[str]
    hair_type: Optional[str]
    hair_length: Optional[str]
    hair_color: Optional[str]
    facial_hair: Optional[str]
    posture: Optional[str]
    skin_markings: Optional[SkinMarkingsModel]
    handedness: Optional[str]
    glasses: Optional[str]
    dist_char_con: Optional[str]
    dist_char_acq: Optional[str]
    physical_habits: Optional[str]
    other: Optional[str]
    phys_name_contact: Optional[str]
    injuries: Optional[str]
    implants: Optional[str]
    malforms: Optional[str]
    pain: Optional[str]
    other_conditions: Optional[str]
    accidents: Optional[str]
    pres_drugs: Optional[str]
    smoker: Optional[str]
    dental_record: Optional[bool]
    dentist_info: Optional[str]
    teeth_features: Optional[str]
    dental_problems: Optional[str]
    dental_treatments: Optional[str]
    dental_habits: Optional[str]
    case_status: Optional[str]
    reporters: Optional[List[ReporterModel]] = Field(default_factory=list)
    identified_by: Optional[str]
    family_notified: Optional[bool]
    hypothesis_based: Optional[str]
    hypothesis_status: Optional[str]
    reburial_location: Optional[str]

    def validate_opts(v, valid_opts):
        if v and len(v):
            if not v.lower() in [x.lower() for x in valid_opts]:
                raise ValueError(f"Invalid value for opts")
        return v

    @validator("publish_date", "documentation_date", pre=True, each_item=True)
    def validate_date(cls, v):
        """
        Validates the date fields.

        Returns:
            str: The validated date value.

        Raises:
            ValueError: If the date is not a valid date.
        """
        if v:
            try:
                parse(v)
            except ValueError:
                raise ValueError(f"Invalid date format: {v}")
        return v

    @validator("*", pre=False)
    def validate_all_opts(cls, v, values, field):
        opts_fields = {
            "pregnant_at_disappearance": Constants.PREGNANT_AT_DISAPPEARANCE_OPTS,
            "smoker": Constants.SMOKER_OPTS,
            "handedness": Constants.HANDEDNESS_OPTS,
            "hair_length": Constants.HAIR_LENGTH_OPTS,
            "hair_type": Constants.HAIR_TYPE_OPTS,
            "hair_color": Constants.HAIR_COLOR_OPTS,
            "hair_loss": Constants.HAIR_LOSS_OPTS,
            "facial_hair": Constants.FACIAL_HAIR_OPTS,
            "physique": Constants.PHYSIQUE_OPTS,
            "case_status": Constants.CASE_STATUS_OPTS,
        }
        if field.name in opts_fields:
            try:
                return PartialActorProfileModel.validate_opts(v, opts_fields[field.name])
            except ValueError as e:
                raise ValueError(f"{e}: {field.name}")
        return v


class ActorValidationModel(StrictValidationModel):
    type: str = DEFAULT_STRING_FIELD  # type: ignore
    name: Optional[str] = DEFAULT_STRING_FIELD
    name_ar: Optional[str] = DEFAULT_STRING_FIELD
    first_name: Optional[str] = DEFAULT_STRING_FIELD
    first_name_ar: Optional[str] = DEFAULT_STRING_FIELD
    middle_name: Optional[str] = DEFAULT_STRING_FIELD
    middle_name_ar: Optional[str] = DEFAULT_STRING_FIELD
    last_name: Optional[str] = DEFAULT_STRING_FIELD
    last_name_ar: Optional[str] = DEFAULT_STRING_FIELD
    father_name: Optional[str] = DEFAULT_STRING_FIELD
    father_name_ar: Optional[str] = DEFAULT_STRING_FIELD
    mother_name: Optional[str] = DEFAULT_STRING_FIELD
    mother_name_ar: Optional[str] = DEFAULT_STRING_FIELD
    sex: Optional[str] = DEFAULT_STRING_FIELD
    age: Optional[str] = DEFAULT_STRING_FIELD
    civilian: Optional[str] = DEFAULT_STRING_FIELD
    occupation: Optional[str] = DEFAULT_STRING_FIELD
    occupation_ar: Optional[str] = DEFAULT_STRING_FIELD
    position: Optional[str] = DEFAULT_STRING_FIELD
    position_ar: Optional[str] = DEFAULT_STRING_FIELD
    family_status: Optional[str] = DEFAULT_STRING_FIELD
    no_children: Optional[str] = DEFAULT_STRING_FIELD
    ethnographies: List[PartialEthnographyModel] = Field(default_factory=list)
    nationalities: List[PartialNationalityModel] = Field(default_factory=list)
    dialects: List[PartialDialectModel] = Field(default_factory=list)
    nickname: Optional[str] = DEFAULT_STRING_FIELD
    nickname_ar: Optional[str] = DEFAULT_STRING_FIELD
    id_number: Optional[str] = DEFAULT_STRING_FIELD
    origin_place: Optional[PartialOriginPlaceModel]
    events: List[PartialEventModel] = Field(default_factory=list)
    medias: List[PartialMediaModel] = Field(default_factory=list)
    actor_relations: List[PartialAtoaModel] = Field(default_factory=list)
    bulletin_relations: List[PartialAtobModel] = Field(default_factory=list)
    incident_relations: List[PartialAtoiModel] = Field(default_factory=list)
    comments: constr(min_length=1)  # type: ignore
    status: Optional[str] = DEFAULT_STRING_FIELD
    actor_profiles: List[PartialActorProfileModel] = Field(default_factory=list)

    # Below fields are sent by the frontend, but are not used by the from_json method
    description: Optional[str] = sanitize()
    updated_at: Optional[str]
    documentation_date: Optional[str]
    publish_date: Optional[str]
    roles: list[PartialRoleModel] = Field(default_factory=list)
    age_: Optional[str] = Field(alias="_age")
    civilian_: Optional[str] = Field(alias="_civilian")
    sex_: Optional[str] = Field(alias="_sex")
    type_: Optional[str] = Field(alias="_type")
    assigned_to: Optional[PartialUserModel]
    class_: Optional[str] = Field(alias="class")
    first_peer_reviewer: Optional[PartialUserModel]
    id: Optional[str]
    review: Optional[str] = sanitize()
    review_action: Optional[str]

    @validator("actor_profiles", always=True, pre=False)
    def check_actor_profiles(cls: t, v: list) -> list:
        """
        Validator function to check if at least one actor profile is provided.

        Args:
            - v: The value of the field being validated.
            - values: The values of all fields in the model up to this validation call.

        Raises:
            - ValueError: If no actor profiles are provided.

        Returns:
            - The validated value.
        """
        if not len(v):
            raise ValueError("At least one actor profile must be provided")
        return v

    @root_validator(pre=False)
    def check_name_rules(cls: t, values: dict) -> dict:
        """
        Validates the name rules based on the type of entity.

        Args:
            - values: The input values to be validated.

        Raises:
            - ValueError: If the type is 'entity' and neither name nor name_ar is provided.
            - ValueError: If the type is 'person' and neither first_name, middle_name, last_name nor first_name_ar, middle_name_ar, last_name_ar is provided.

        Returns:
            - The validated values.
        """
        # If type is 'entity' either name or name_ar must be provided
        if values.get("type").lower() == "entity":
            if not values.get("name") and not values.get("name_ar"):
                raise ValueError("Either name or name_ar must be provided for entity type")
        else:
            if not (
                values.get("first_name") or values.get("middle_name") or values.get("last_name")
            ) and not (
                values.get("first_name_ar")
                or values.get("middle_name_ar")
                or values.get("last_name_ar")
            ):
                raise ValueError(
                    "At least one of first_name, middle_name, last_name or first_name_ar, middle_name_ar, last_name_ar must be provided for person type"
                )
        return values

    @validator("publish_date", "documentation_date", pre=True, each_item=True)
    def validate_date(cls, v):
        """
        Validates the date fields.

        Returns:
            str: The validated date value.

        Raises:
            ValueError: If the date is not a valid date.
        """
        if v:
            try:
                parse(v)
            except ValueError:
                raise ValueError(f"Invalid date format: {v}")
        return v


class ActorRequestModel(BaseValidationModel):
    item: ActorValidationModel


class LabelValidationModel(StrictValidationModel):
    title: constr(min_length=1)  # type: ignore
    title_ar: Optional[str]
    comments: Optional[str]
    comments_ar: Optional[str]
    verified: Optional[bool] = False
    for_bulletin: Optional[bool] = False
    for_actor: Optional[bool] = False
    for_incident: Optional[bool] = False
    for_offline: Optional[bool] = False
    parent: Optional[PartialLabelModel] = None
    # below fields are sent by the frontend, discarded by from_json
    id: Optional[int]
    order: Optional[int]
    updated_at: Optional[str]


class LabelRequestModel(BaseValidationModel):
    item: LabelValidationModel


class EventtypeValidationModel(one_must_exist(["title", "title_ar"])):
    title: Optional[str]
    title_ar: Optional[str]
    for_actor: Optional[bool]
    for_bulletin: Optional[bool]
    comments: Optional[str]
    # sent by the front-end on PUT, but not used by the from_json method
    id: Optional[int]
    updated_at: Optional[str]


class EventtypeRequestModel(BaseValidationModel):
    item: EventtypeValidationModel


class PotentialViolationValidationModel(StrictValidationModel):
    title: constr(min_length=1)  # type: ignore
    # sent by the front-end on PUT, but not used by the from_json method
    title_ar: Optional[str]
    id: Optional[int]
    updated_at: Optional[str]


class PotentialViolationRequestModel(BaseValidationModel):
    item: PotentialViolationValidationModel


class ClaimedViolationValidationModel(StrictValidationModel):
    title: constr(min_length=1)  # type: ignore
    # sent by the front-end on PUT, but not used by the from_json method
    title_ar: Optional[str]
    id: Optional[int]
    updated_at: Optional[str]


class ClaimedViolationRequestModel(BaseValidationModel):
    item: ClaimedViolationValidationModel


class SourceValidationModel(StrictValidationModel):
    title: constr(min_length=1)  # type: ignore
    title_ar: Optional[str]
    comments: Optional[str]
    comments_ar: Optional[str]
    parent: Optional[PartialSourceModel]
    # sent by the front-end on PUT, but not used by the from_json method
    id: Optional[int]
    updated_at: Optional[str]
    etl_id: Optional[str]


class SourceRequestModel(BaseValidationModel):
    item: SourceValidationModel


class AdminLevelModel(BaseValidationModel):
    id: int
    code: int
    title: constr(min_length=1)  # type: ignore


class LatLngModel(BaseValidationModel):
    lat: float
    lng: float


class LocationTypeModel(BaseValidationModel):
    id: int
    title: constr(min_length=1)  # type: ignore
    description: Optional[str] = sanitize()


class LocationValidationModel(one_must_exist(["title", "title_ar"])):
    title: Optional[str]
    title_ar: Optional[str]
    description: Optional[str] = sanitize()
    parent: Optional[PartialLocationModel]  # type: ignore
    country: Optional[dict]
    postal_code: Optional[str]
    latlng: Optional[LatLngModel]
    location_type: Optional[LocationTypeModel]
    admin_level: Optional[
        AdminLevelModel | str
    ]  # if the location_type is POI, front end sends an empty str for admin_level

    # sent by the front-end on PUT, but not used by the from_json method
    id: Optional[int]
    updated_at: Optional[str]
    tags: Optional[List[str]] = Field(default_factory=list)
    lat: Optional[float]
    lng: Optional[float]
    full_location: Optional[str]
    full_string: Optional[str]
    ctitle: Optional[str]

    @validator("admin_level", always=True, pre=False)
    def check_admin_level(cls: t, v: Any, values: dict) -> Any:
        """
        Validates the 'admin_level' field if location_type is AdminLevel.

        Args:
            - v: The value of the 'admin_level' field.
            - values: The dictionary of values for the model up to this validation call.

        Raises:
            - ValueError: If 'admin_level' is not a valid AdminLevelModel or if it is not provided.

        Returns:
            - The validated value of 'admin_level'.
        """
        if (
            values.get("location_type")
            and values["location_type"].title == "Administrative Location"
        ):
            if isinstance(v, str):
                raise ValueError("admin_level must be a valid AdminLevelModel, not str")
            if v is None:
                raise ValueError("admin_level must be provided")
        return v


LocationValidationModel.update_forward_refs()


class LocationRequestModel(BaseValidationModel):
    item: LocationValidationModel


class LatLngRadiusModel(LatLngModel):
    radius: int


class PartialLocationTypeModel(BaseValidationModel):
    id: int


class PartialAdminLevelModel(BaseValidationModel):
    id: int
    code: int


class PartialCountryModel(BaseValidationModel):
    id: int


class LocationQueryValidationModel(StrictValidationModel):
    lvl: Optional[int]
    title: Optional[str]
    tsv: Optional[str]
    latlng: Optional[LatLngRadiusModel]
    location_type: Optional[PartialLocationTypeModel]
    admin_level: Optional[PartialAdminLevelModel]
    country: Optional[PartialCountryModel]
    tags: Optional[str]
    optags: Optional[bool]


class OptionsModel(BaseValidationModel):
    page: Optional[int]
    itemsPerPage: Optional[int]


class LocationQueryRequestModel(BaseValidationModel):
    q: LocationQueryValidationModel
    options: OptionsModel


class LocationAdminLevelValidationModel(StrictValidationModel):
    title: constr(min_length=1)  # type: ignore
    code: int
    id: Optional[int]


class LocationAdminLevelRequestModel(BaseValidationModel):
    item: LocationAdminLevelValidationModel


class LocationTypeValidationModel(StrictValidationModel):
    title: constr(min_length=1)  # type: ignore
    # sent by the front-end on PUT, but not used by the from_json method
    id: Optional[int]
    description: Optional[str] = sanitize()


class LocationTypeRequestModel(BaseValidationModel):
    item: LocationTypeValidationModel


class CountryValidationModel(StrictValidationModel):
    title: constr(min_length=1)  # type: ignore
    title_tr: Optional[str]
    # sent by the front-end on PUT, but not used by the from_json method
    id: Optional[int]
    created_at: Optional[str]
    updated_at: Optional[str]


class CountryRequestModel(BaseValidationModel):
    item: CountryValidationModel


class ComponentDataMixinValidationModel(BaseValidationModel):
    id: Optional[int]
    title: constr(min_length=1)  # type: ignore
    title_tr: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    deleted: Optional[bool]


class ComponentDataMixinRequestModel(BaseValidationModel):
    item: ComponentDataMixinValidationModel


class AtoaInfoValidationModel(StrictValidationModel):
    title: constr(min_length=1)  # type: ignore
    reverse_title: constr(min_length=1)  # type: ignore
    title_tr: Optional[str]
    reverse_title_tr: Optional[str]
    id: Optional[int]


class AtoaInfoRequestModel(BaseValidationModel):
    item: AtoaInfoValidationModel


class AtobInfoValidationModel(StrictValidationModel):
    title: constr(min_length=1)  # type: ignore
    title_tr: Optional[str]
    id: Optional[int]
    reverse_title: Optional[str]
    reverse_title_tr: Optional[str]


class AtobInfoRequestModel(BaseValidationModel):
    item: AtobInfoValidationModel


class BtobInfoValidationModel(StrictValidationModel):
    title: constr(min_length=1)  # type: ignore
    title_tr: Optional[str]
    id: Optional[int]
    reverse_title: Optional[str]
    reverse_title_tr: Optional[str]


class BtobInfoRequestModel(BaseValidationModel):
    item: BtobInfoValidationModel


class ItoaInfoValidationModel(StrictValidationModel):
    title: constr(min_length=1)  # type: ignore
    title_tr: Optional[str]
    id: Optional[int]
    reverse_title: Optional[str]
    reverse_title_tr: Optional[str]


class ItoaInfoRequestModel(BaseValidationModel):
    item: ItoaInfoValidationModel


class ItobInfoValidationModel(StrictValidationModel):
    title: constr(min_length=1)  # type: ignore
    title_tr: Optional[str]
    id: Optional[int]
    reverse_title: Optional[str]
    reverse_title_tr: Optional[str]


class ItobInfoRequestModel(BaseValidationModel):
    item: ItobInfoValidationModel


class ItoiInfoValidationModel(StrictValidationModel):
    title: constr(min_length=1)  # type: ignore
    title_tr: Optional[str]
    id: Optional[int]
    reverse_title: Optional[str]
    reverse_title_tr: Optional[str]


class ItoiInfoRequestModel(BaseValidationModel):
    item: ItoiInfoValidationModel


class MediaCategoryValidationModel(StrictValidationModel):
    title: constr(min_length=1)  # type: ignore
    title_tr: Optional[str]
    # sent by the front-end on PUT, but not used by the from_json method
    id: Optional[int]
    created_at: Optional[str]
    updated_at: Optional[str]


class MediaCategoryRequestModel(BaseValidationModel):
    item: MediaCategoryValidationModel


class GeoLocationTypeValidationModel(StrictValidationModel):
    title: constr(min_length=1)  # type: ignore
    title_tr: Optional[str]
    # sent by the front-end on PUT, but not used by the from_json method
    id: Optional[int]
    created_at: Optional[str]
    updated_at: Optional[str]


class GeoLocationTypeRequestModel(BaseValidationModel):
    item: GeoLocationTypeValidationModel


class PartialEventTypeModel(BaseValidationModel):
    id: int


class QueryBaseModel(StrictValidationModel):
    tsv: Optional[str]
    extsv: Optional[str]
    labels: Optional[List[PartialLabelModel]]
    oplabels: Optional[bool]
    exlabels: Optional[List[PartialLabelModel]]
    opvlabels: Optional[bool]
    vlabels: Optional[List[PartialLabelModel]]
    exvlabels: Optional[List[PartialLabelModel]]
    opsources: Optional[bool]
    sources: Optional[List[PartialSourceModel]]
    exsources: Optional[List[PartialSourceModel]]
    locations: Optional[List[PartialLocationModel]]
    oplocations: Optional[bool]
    exlocations: Optional[List[PartialLocationModel]]
    created: Optional[List[str]]
    updated: Optional[List[str]]
    docdate: Optional[List[str]]
    pubdate: Optional[List[str]]
    singleEvent: Optional[bool]
    edate: Optional[List[str]]
    etype: Optional[PartialEventTypeModel]
    elocation: Optional[PartialLocationModel]
    roles: Optional[List[int]]
    norole: Optional[bool]
    assigned: Optional[List[int]]
    fpr: Optional[List[int]] = Field(default_factory=list)
    unassigned: Optional[bool]
    reviewer: Optional[List[int]]
    statuses: Optional[List[str]]
    reviewAction: Optional[str]
    rel_to_bulletin: Optional[int]
    rel_to_actor: Optional[int]
    rel_to_incident: Optional[int]

    @root_validator(pre=True)
    def check_legacy_fields(cls, values):
        """
        Checks the legacy date and status fields, throws an error if they are present.
        """
        old_fields = ["createdwithin", "updatedwithin", "docdatewithin", "pubdatewithin", "status"]
        for field in old_fields:
            if field in values:
                raise ValueError(
                    f"The query sent is incompatible with this version. Please delete and re-create the query."
                )
        return values

    @validator("updated", "created", "docdate", "pubdate", "edate", pre=True, each_item=True)
    def validate_date(cls, v):
        """
        Validates the date fields.

        Returns:
            str: The validated date value.

        Raises:
            ValueError: If the date is not a valid date.
        """
        if v:
            try:
                parse(v)
            except ValueError:
                raise ValueError(f"Invalid date format: {v}")
        return v


class BulletinQueryLocTypes(Enum):
    LOCATIONS = "locations"
    GEMOARKERS = "geomarkers"
    EVENTS = "events"


class BulletinQueryValidationModel(QueryBaseModel):
    op: Optional[str] = "or"
    ids: List[int] = Field(default_factory=list)
    ref: Optional[List[str]] = Field(default_factory=list)
    inExact: Optional[bool] = False
    opref: Optional[bool] = False
    exref: Optional[List[str]] = Field(default_factory=list)
    exExact: Optional[bool] = False
    opexref: Optional[bool] = False
    childlabels: Optional[bool] = False
    childverlabels: Optional[bool] = False
    childsources: Optional[bool] = False
    locTypes: Optional[List[str]] = Field(default_factory=list)
    latlng: Optional[LatLngRadiusModel]

    @validator("ref", pre=True)
    def validate_ref(cls, v):
        """
        Validates the ref field.

        Returns:
            List<str>: The validated ref value.
        """
        if isinstance(v, str):
            v = [v]
        return v


class BulletinQueryRequestModel(BaseValidationModel):
    q: List[BulletinQueryValidationModel] = Field(default_factory=list)


class EntityReviewValidationModel(BaseValidationModel):
    review: Optional[str] = sanitize()
    review_action: Optional[str]


class BulletinReviewValidationModel(EntityReviewValidationModel):
    revrefs: List[str] = Field(default_factory=list)


class BulletinReviewRequestModel(BaseValidationModel):
    item: BulletinReviewValidationModel


class GenericBulkModel(BaseValidationModel):
    status: Optional[str]
    assigned_to_id: Optional[int]
    first_peer_reviewer_id: Optional[int]
    comments: Optional[str]
    roles: List[PartialRoleModel] = Field(default_factory=list)
    rolesReplace: Optional[bool]
    assigneeClear: Optional[bool]
    reviewerClear: Optional[bool]


class BulletinBulkModel(GenericBulkModel):
    ref: List[str] = Field(default_factory=list)
    refReplace: Optional[bool]


class IncidentBulkModel(GenericBulkModel):
    assignRelated: Optional[bool]
    restrictRelated: Optional[bool]


class IncidentBulkUpdateRequestModel(BaseValidationModel):
    items: List[int]
    bulk: IncidentBulkModel


class BulletinBulkUpdateRequestModel(BaseValidationModel):
    items: List[int]
    bulk: BulletinBulkModel


class BulkUpdateRequestModel(BaseValidationModel):
    items: List[int]
    bulk: GenericBulkModel


class GenericSelfAssignValidationModel(BaseValidationModel):
    comments: Optional[str]


class BulletinSelfAssignValidationModel(GenericSelfAssignValidationModel):
    ref: List[str] = Field(default_factory=list)


class BulletinSelfAssignRequestModel(BaseValidationModel):
    bulletin: BulletinSelfAssignValidationModel


class ActorSelfAssignRequestModel(BaseValidationModel):
    actor: GenericSelfAssignValidationModel


class IncidentSelfAssignRequestModel(BaseValidationModel):
    incident: GenericSelfAssignValidationModel


class MediaValidationModel(PartialMediaModel):
    pass


class MediaRequestModel(BaseModel):
    item: MediaValidationModel


class ActorQueryLocTypes(Enum):
    ORIGIN_PLACE = "originplace"
    EVENTS = "events"


class ActorQueryModel(QueryBaseModel):
    op: Optional[str] = "or"
    nickname: Optional[str]
    first_name: Optional[str]
    middle_name: Optional[str]
    last_name: Optional[str]
    father_name: Optional[str]
    mother_name: Optional[str]
    opEthno: Optional[bool]
    ethnography: List[PartialEthnographyModel] = Field(default_factory=list)
    opNat: Optional[bool]
    nationality: List[PartialNationalityModel] = Field(default_factory=list)
    resLocations: List[PartialLocationModel] = Field(default_factory=list)
    originLocations: List[PartialLocationModel] = Field(default_factory=list)
    exResLocations: List[PartialLocationModel] = Field(default_factory=list)
    exOriginLocations: List[PartialLocationModel] = Field(default_factory=list)
    occupation: Optional[str]
    position: Optional[str]
    opDialects: Optional[bool]
    dialects: List[PartialDialectModel] = Field(default_factory=list)
    family_status: Optional[str]
    sex: Optional[str]
    age: Optional[str]
    civilian: Optional[str]
    type_: Optional[str] = Field(alias="type")
    id_number: Optional[str]
    locTypes: List[str] = Field(default_factory=list)
    latlng: Optional[LatLngRadiusModel]


class ActorQueryRequestModel(BaseValidationModel):
    q: List[ActorQueryModel] = Field(default_factory=list)


class ActorReviewRequestModel(BaseValidationModel):
    item: EntityReviewValidationModel


class UserValidationModel(StrictValidationModel):
    email: Optional[str]
    username: constr(min_length=1)  # type: ignore
    password: Optional[str]  # Optional on PUT, required on POST
    name: constr(min_length=1)  # type: ignore
    roles: List[PartialRoleModel] = Field(default_factory=list)
    view_usernames: Optional[bool]
    view_full_history: Optional[bool]
    view_simple_history: Optional[bool]
    can_self_assign: Optional[bool]
    can_edit_locations: Optional[bool]
    can_export: Optional[bool]
    active: bool
    force_reset: Optional[str]
    google_id: Optional[str]
    id: Optional[int]
    two_factor_devices: Optional[Any]


class UserRequestModel(BaseValidationModel):
    item: UserValidationModel


class UserNameCheckValidationModel(BaseValidationModel):
    item: constr(min_length=1)  # type: ignore


class UserPasswordCheckValidationModel(BaseValidationModel):
    password: constr(min_length=1)  # type: ignore


class UserForceResetRequestModel(BaseValidationModel):
    item: PartialUserModel


class RoleValidationModel(BaseValidationModel):
    name: constr(min_length=1)  # type: ignore
    description: Optional[str]
    color: constr(min_length=1)  # type: ignore
    id: Optional[int]


class RoleRequestModel(BaseValidationModel):
    item: RoleValidationModel


class IncidentQueryModel(QueryBaseModel):
    potentialVCats: List[PartialPotentialViolationModel] = Field(default_factory=list)
    claimedVCats: List[PartialClaimedViolationModel] = Field(default_factory=list)


class IncidentQueryRequestModel(BaseValidationModel):
    q: Optional[IncidentQueryModel]


class IncidentReviewRequestModel(BaseValidationModel):
    item: EntityReviewValidationModel


class QueryValidationModel(BaseValidationModel):
    q: Dict[str, Any] = Field(default_factory=dict)
    name: Optional[str]
    # Optional on PUT, required on POST
    type_: Optional[str] = Field(alias="type")


class GraphVisualizeRequestModel(BaseValidationModel):
    q: List[Dict[str, Any]] | Dict[str, Any]


class ConfigRequestModel(BaseValidationModel):
    conf: Dict[Any, Any]
