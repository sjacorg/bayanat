from enum import Enum
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
    HttpUrl,
    ValidationInfo,
)
from typing import Optional, Any, List, Dict
from urllib.parse import urlparse
from dateutil.parser import parse
import re

from enferno.admin.constants import Constants
from enferno.admin.models import Activity, AppConfig
from enferno.settings import Config
from enferno.utils.config_utils import ConfigManager
from enferno.utils.validation_utils import SanitizedField, one_must_exist
from enferno.utils.typing import typ as t
from enferno.utils.validation_utils import (
    validate_email_format,
    validate_password_policy,
    validate_username_constraints,
    validate_field_type,
)
from enferno.admin.models.DynamicField import DynamicField
from wtforms.validators import ValidationError

DEFAULT_STRING_FIELD = Field(default=None, max_length=255)

BASE_MODEL_CONFIG = ConfigDict(str_strip_whitespace=True)
STRICT_MODEL_CONFIG = ConfigDict(str_strip_whitespace=True, extra="forbid")

PER_PAGE = int(Config.get("ITEMS_PER_PAGE_OPTIONS")[0])


def validate_dynamic_fields(entity_type: str, model_instance) -> None:
    """Validate dynamic fields against their schema definitions."""
    # Use model_extra to get only true extra fields (not aliases)
    dynamic_data = model_instance.model_extra or {}

    if not dynamic_data:
        return

    fields = DynamicField.query.filter_by(entity_type=entity_type, active=True, core=False).all()
    field_map = {f.name: f for f in fields}

    for name, value in dynamic_data.items():
        if name not in field_map:
            raise ValueError(f"Unknown field '{name}' for {entity_type}")
        validated = validate_field_type(value, field_map[name].field_type)
        setattr(model_instance, name, validated)


class BaseValidationModel(BaseModel):
    """Base class for all validation models."""

    model_config = BASE_MODEL_CONFIG


class StrictValidationModel(BaseModel):
    """Base class that forbids extra fields in the model."""

    model_config = STRICT_MODEL_CONFIG


class PartialUserModel(BaseValidationModel):
    id: int


class PartialRoleModel(BaseValidationModel):
    id: int
    color: Optional[str] = None
    description: Optional[SanitizedField] = None
    name: Optional[str] = None


class PartialLocationModel(BaseValidationModel):
    id: int


class PartialGeoLocationTypeModel(BaseValidationModel):
    id: Optional[int] = None


class PartialSourceModel(BaseValidationModel):
    id: int


class PartialLabelModel(BaseValidationModel):
    id: int


class PartialGeoLocationModel(BaseValidationModel):
    id: Optional[int] = None
    title: str = Field(min_length=1)
    geotype: Optional[PartialGeoLocationTypeModel] = None
    main: Optional[bool] = None
    lng: float
    lat: float
    comment: Optional[str] = None


class PartialEventLocationModel(BaseValidationModel):
    id: Optional[int] = None


class PartialEventtypeModel(BaseValidationModel):
    id: Optional[int] = None


class PartialManyRelationModel(BaseValidationModel):
    probability: Optional[int] = None
    comment: Optional[str] = None
    related_as: Optional[list[int]] = Field(default_factory=list)


class PartialSingleRelationModel(BaseValidationModel):
    probability: Optional[int] = None
    comment: Optional[str] = None
    related_as: Optional[int] = None


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
    id: Optional[int] = None
    title: Optional[str] = None
    title_ar: Optional[str] = None
    comments: Optional[str] = None
    comments_ar: Optional[str] = None
    location: Optional[PartialEventLocationModel] = None
    eventtype: Optional[PartialEventtypeModel] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    estimated: Optional[bool] = None

    @field_validator("from_date", "to_date")
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

    @model_validator(mode="after")
    def validate_to_date(self) -> "PartialEventModel":
        """
        Validates the to_date field.

        Returns:
            PartialEventModel: The validated model instance.

        Raises:
            ValueError: If the to_date is before the from_date.
        """
        if self.from_date and self.to_date:
            from_date = parse(self.from_date)
            to_date = parse(self.to_date)
            if to_date < from_date:
                raise ValueError("to_date must be after from_date")
        return self


class PartialMediaCategoryModel(BaseValidationModel):
    id: Optional[int] = None


class PartialMediaModel(BaseValidationModel):
    id: Optional[int] = None
    main: Optional[bool] = None
    title: Optional[str] = None
    title_ar: Optional[str] = None
    fileType: Optional[str] = None
    filename: Optional[str] = None
    etag: Optional[str] = None
    time: Optional[Any] = None
    category: Optional[PartialMediaCategoryModel] = None


class BulletinValidationModel(StrictValidationModel):
    # Allow unknown/dynamic fields to pass through to from_json
    model_config = ConfigDict(str_strip_whitespace=True, extra="allow")

    originid: Optional[str] = None
    title: str = Field(min_length=1)
    sjac_title: Optional[str] = None
    assigned_to: Optional[PartialUserModel] = None
    first_peer_reviewer: Optional[PartialUserModel] = None
    description: Optional[SanitizedField] = None
    comments: str = Field(min_length=1)
    source_link: str = Field(min_length=1)
    source_link_type: Optional[bool] = None
    tags: Optional[list[str]] = Field(default_factory=list)
    locations: list[PartialLocationModel] = Field(default_factory=list)
    geoLocations: list[PartialGeoLocationModel] = Field(default_factory=list)
    sources: list[PartialSourceModel] = Field(default_factory=list)
    labels: list[PartialLabelModel] = Field(default_factory=list)
    verLabels: list[PartialLabelModel] = Field(default_factory=list)
    events: list[PartialEventModel] = Field(default_factory=list)
    medias: list[PartialMediaModel] = Field(default_factory=list)
    bulletin_relations: list[PartialBtobModel] = Field(default_factory=list)
    actor_relations: list[PartialBtoaModel] = Field(default_factory=list)
    incident_relations: list[PartialBtoiModel] = Field(default_factory=list)

    publish_date: Optional[str] = None
    documentation_date: Optional[str] = None
    status: Optional[str] = None

    roles: list[PartialRoleModel] = Field(default_factory=list)

    id: Optional[int] = None
    review: Optional[SanitizedField] = None
    review_action: Optional[str] = None
    sjac_title_ar: Optional[str] = None
    title_ar: Optional[str] = None
    updated_at: Optional[str] = None
    class_: Optional[str] = Field(default=None, alias="class")

    @field_validator("source_link", mode="before")
    def validate_source_link(cls: t, v: str) -> str:
        """
        Validates the source_link field.

        Args:
            - v: The value of the source_link field.

        Raises:
            - ValueError: If the source_link is not a valid URL, a valid file path, or 'NA'.

        Returns:
            - The validated source_link value.
        """
        if v and v != "NA":
            parsed_url = urlparse(v)
            is_valid_url = all([parsed_url.scheme, parsed_url.netloc])

            unix_pattern = r"^(/[^/\0]+)+/?$"

            is_valid_path = re.match(unix_pattern, v) is not None

            if not is_valid_url and not is_valid_path:
                raise ValueError("source_link must be a valid URL, a valid file path, or 'NA'")
        return v

    @field_validator("publish_date", "documentation_date", mode="before")
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

    @model_validator(mode="after")
    def validate_bulletin_dynamic_fields(self):
        """Validate dynamic bulletin fields."""
        validate_dynamic_fields("bulletin", self)
        return self


class BulletinRequestModel(BaseValidationModel):
    item: BulletinValidationModel


class PartialPotentialViolationModel(BaseValidationModel):
    id: int


class PartialClaimedViolationModel(BaseValidationModel):
    id: int


class IncidentValidationModel(StrictValidationModel):
    # Allow unknown/dynamic fields to pass through to from_json
    model_config = ConfigDict(str_strip_whitespace=True, extra="allow")

    title: str = Field(min_length=1)
    title_ar: Optional[str] = None
    description: Optional[SanitizedField] = None
    labels: list[PartialLabelModel] = Field(default_factory=list)
    locations: list[PartialLocationModel] = Field(default_factory=list)
    potential_violations: list[PartialPotentialViolationModel] = Field(default_factory=list)
    claimed_violations: list[PartialClaimedViolationModel] = Field(default_factory=list)
    events: list[PartialEventModel] = Field(default_factory=list)
    check_ar: Optional[bool] = None
    check_ir: Optional[Any] = None
    check_br: Optional[Any] = None
    actor_relations: list[PartialItoaModel] = Field(default_factory=list)
    bulletin_relations: list[PartialItobModel] = Field(default_factory=list)
    incident_relations: list[PartialItoiModel] = Field(default_factory=list)
    comments: str = Field(min_length=1)
    status: Optional[str] = None

    # Below fields are sent by the front-end, dismissed by `from_json`
    documentation_date: Optional[str] = None
    publish_date: Optional[str] = None
    assigned_to: Optional[PartialUserModel] = None
    first_peer_reviewer: Optional[PartialUserModel] = None
    id: Optional[int] = None
    class_: Optional[str] = Field(alias="class", default=None)
    review: Optional[SanitizedField] = None
    review_action: Optional[str] = None
    updated_at: Optional[str] = None
    roles: list[PartialRoleModel] = Field(default_factory=list)

    @field_validator("actor_relations")
    @classmethod
    def check_actor_relations(cls, v: list, info: ValidationInfo) -> list:
        """
        Check the validity of actor_relations field.

        Args:
            v: The value of the actor_relations field
            info: ValidationInfo containing the model's data during validation

        Raises:
            ValueError: If actor_relations provided without check_ar

        Returns:
            The validated actor_relations list
        """
        if not len(v):
            return []
        if (v and len(v)) and "check_ar" not in info.data:
            raise ValueError("actor_relations provided without check_ar")
        return v

    @field_validator("bulletin_relations")
    def check_bulletin_relations(cls: t, v: list, info: ValidationInfo) -> list:
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
        if (v and len(v)) and "check_br" not in info.data:
            raise ValueError("bulletin_relations provided without check_br")
        return v

    @field_validator("incident_relations")
    def check_incident_relations(cls: t, v: list, info: ValidationInfo) -> list:
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
        if (v and len(v)) and "check_ir" not in info.data:
            raise ValueError("incident_relations provided without check_ir")
        return v

    @field_validator("publish_date", "documentation_date")
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

    @model_validator(mode="after")
    def validate_incident_dynamic_fields(self):
        """Validate dynamic incident fields."""
        validate_dynamic_fields("incident", self)
        return self


class IncidentRequestModel(BaseValidationModel):
    item: IncidentValidationModel


class PartialEthnographyModel(BaseValidationModel):
    id: int


class PartialNationalityModel(BaseValidationModel):
    id: int


class PartialDialectModel(BaseValidationModel):
    id: int


class PartialOriginPlaceModel(BaseValidationModel):
    id: Optional[int] = None


class OptsModel(BaseValidationModel):
    opts: Optional[str] = None
    details: Optional[str] = None

    @field_validator("opts")
    def validate_opts(cls, v):
        """
        Validates the opts field.

        Returns:
            str: The validated opts value.

        Raises:
            ValueError: If the opts is not a valid value.
        """
        if v and len(v):
            if v.lower() not in [x.lower() for x in Constants.CLASSIC_OPTS]:
                raise ValueError("Invalid value for opts")
        return v


class SkinMarkingsModel(BaseValidationModel):
    opts: Optional[list[str]] = Field(default_factory=list)
    details: Optional[str] = None

    @field_validator("opts")
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
    name: Optional[str] = None
    contact: Optional[str] = None
    relationship: Optional[str] = None


class PartialActorProfileModel(BaseValidationModel):
    id: Optional[int] = None
    actor_id: Optional[int] = None
    mode: int = 1
    originid: Optional[str] = None
    description: Optional[SanitizedField] = None
    source_link: Optional[str] = DEFAULT_STRING_FIELD
    source_link_type: Optional[bool] = None
    publish_date: Optional[str] = None
    documentation_date: Optional[str] = None
    sources: list[PartialSourceModel] = Field(default_factory=list)
    labels: list[PartialLabelModel] = Field(default_factory=list)
    ver_labels: list[PartialLabelModel] = Field(default_factory=list)
    # Fields below are required if mode==3
    last_address: Optional[str] = None
    marriage_history: Optional[str] = None
    pregnant_at_disappearance: Optional[str] = None
    months_pregnant: Optional[int] = None
    missing_relatives: Optional[bool] = None
    saw_name: Optional[str] = None
    saw_address: Optional[str] = None
    saw_email: Optional[str] = None
    saw_phone: Optional[str] = None
    seen_in_detention: Optional[OptsModel] = None
    eye_color: Optional[str] = None
    injured: Optional[OptsModel] = None
    known_dead: Optional[OptsModel] = None
    death_details: Optional[str] = None
    personal_items: Optional[str] = None
    height: Optional[int] = None
    weight: Optional[int] = None
    physique: Optional[str] = None
    hair_loss: Optional[str] = None
    hair_type: Optional[str] = None
    hair_length: Optional[str] = None
    hair_color: Optional[str] = None
    facial_hair: Optional[str] = None
    posture: Optional[str] = None
    skin_markings: Optional[SkinMarkingsModel] = None
    handedness: Optional[str] = None
    glasses: Optional[str] = None
    dist_char_con: Optional[str] = None
    dist_char_acq: Optional[str] = None
    physical_habits: Optional[str] = None
    other: Optional[str] = None
    phys_name_contact: Optional[str] = None
    injuries: Optional[str] = None
    implants: Optional[str] = None
    malforms: Optional[str] = None
    pain: Optional[str] = None
    other_conditions: Optional[str] = None
    accidents: Optional[str] = None
    pres_drugs: Optional[str] = None
    smoker: Optional[str] = None
    dental_record: Optional[bool] = None
    dentist_info: Optional[str] = None
    teeth_features: Optional[str] = None
    dental_problems: Optional[str] = None
    dental_treatments: Optional[str] = None
    dental_habits: Optional[str] = None
    case_status: Optional[str] = None
    reporters: Optional[list[ReporterModel]] = Field(default_factory=list)
    identified_by: Optional[str] = None
    family_notified: Optional[bool] = None
    hypothesis_based: Optional[str] = None
    hypothesis_status: Optional[str] = None
    reburial_location: Optional[str] = None

    @classmethod
    def validate_opts(cls, v, valid_opts):
        if v and len(v):
            if v.lower() not in [x.lower() for x in valid_opts]:
                raise ValueError("Invalid value for opts")
        return v

    @field_validator("publish_date", "documentation_date")
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

    @field_validator(
        "pregnant_at_disappearance",
        "smoker",
        "handedness",
        "hair_length",
        "hair_type",
        "hair_color",
        "hair_loss",
        "facial_hair",
        "physique",
        "case_status",
    )
    @classmethod
    def validate_all_opts(cls, v: Any, info: ValidationInfo) -> Any:
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
        field_name = info.field_name
        if field_name in opts_fields:
            try:
                return PartialActorProfileModel.validate_opts(v, opts_fields[field_name])
            except ValueError as e:
                raise ValueError(f"{e}: {field_name}")
        return v


class ActorValidationModel(StrictValidationModel):
    # Allow unknown/dynamic fields to pass through to from_json
    model_config = ConfigDict(str_strip_whitespace=True, extra="allow")

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
    no_children: Optional[int] = None
    ethnographies: list[PartialEthnographyModel] = Field(default_factory=list)
    nationalities: list[PartialNationalityModel] = Field(default_factory=list)
    dialects: list[PartialDialectModel] = Field(default_factory=list)
    nickname: Optional[str] = DEFAULT_STRING_FIELD
    nickname_ar: Optional[str] = DEFAULT_STRING_FIELD
    id_number: list[dict[str, str]] = Field(default_factory=list)
    origin_place: Optional[PartialOriginPlaceModel] = None
    events: list[PartialEventModel] = Field(default_factory=list)
    medias: list[PartialMediaModel] = Field(default_factory=list)
    actor_relations: list[PartialAtoaModel] = Field(default_factory=list)
    bulletin_relations: list[PartialAtobModel] = Field(default_factory=list)
    incident_relations: list[PartialAtoiModel] = Field(default_factory=list)
    comments: str = Field(min_length=1)  # type: ignore
    status: Optional[str] = DEFAULT_STRING_FIELD
    actor_profiles: list[PartialActorProfileModel] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    # Below fields are sent by the frontend, but are not used by the from_json method
    description: Optional[SanitizedField] = None
    updated_at: Optional[str] = None
    documentation_date: Optional[str] = None
    publish_date: Optional[str] = None
    roles: list[PartialRoleModel] = Field(default_factory=list)
    age_: Optional[str] = Field(default=None, alias="_age")
    civilian_: Optional[str] = Field(default=None, alias="_civilian")
    sex_: Optional[str] = Field(default=None, alias="_sex")
    type_: Optional[str] = Field(default=None, alias="_type")
    assigned_to: Optional[PartialUserModel] = None
    class_: Optional[str] = Field(default=None, alias="class")
    first_peer_reviewer: Optional[PartialUserModel] = None
    id: Optional[int] = None
    review: Optional[SanitizedField] = None
    review_action: Optional[str] = None

    @field_validator("no_children")
    def validate_no_children(cls, v):
        if v is not None and v < 0:
            raise ValueError("Number of children must be a non-negative integer")
        elif v is not None and v > 1000:
            raise ValueError("Number of children must be less than 1000")
        return v

    @field_validator("actor_profiles")
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

    @model_validator(mode="after")
    def check_name_rules(self) -> "ActorValidationModel":
        """
        Validates the name rules based on the type of entity.

        Raises:
            - ValueError: If the type is 'entity' and neither name nor name_ar is provided.
            - ValueError: If the type is 'person' and neither first_name, middle_name, last_name nor first_name_ar, middle_name_ar, last_name_ar is provided.

        Returns:
            - The validated model instance.
        """
        # If type is 'entity' either name or name_ar must be provided
        if self.type.lower() == "entity":
            if not self.name and not self.name_ar:
                raise ValueError("Either name or name_ar must be provided for entity type")
        else:
            if not (self.first_name or self.middle_name or self.last_name) and not (
                self.first_name_ar or self.middle_name_ar or self.last_name_ar
            ):
                raise ValueError(
                    "At least one of first_name, middle_name, last_name or first_name_ar, middle_name_ar, last_name_ar must be provided for person type"
                )
        return self

    @field_validator("publish_date", "documentation_date")
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

    @model_validator(mode="after")
    def validate_actor_dynamic_fields(self):
        """Validate dynamic actor fields."""
        validate_dynamic_fields("actor", self)
        return self


class ActorRequestModel(BaseValidationModel):
    item: ActorValidationModel


class LabelValidationModel(StrictValidationModel):
    title: str = Field(min_length=1)
    title_ar: Optional[str] = None
    comments: Optional[str] = None
    comments_ar: Optional[str] = None
    verified: Optional[bool] = False
    for_bulletin: Optional[bool] = False
    for_actor: Optional[bool] = False
    for_incident: Optional[bool] = False
    for_offline: Optional[bool] = False
    parent: Optional[PartialLabelModel] = None
    # below fields are sent by the frontend, discarded by from_json
    id: Optional[int] = None
    order: Optional[int] = None
    updated_at: Optional[str] = None


class LabelRequestModel(BaseValidationModel):
    item: LabelValidationModel


class EventtypeValidationModel(one_must_exist(["title", "title_ar"])):
    title: Optional[str] = None
    title_ar: Optional[str] = None
    for_actor: Optional[bool] = None
    for_bulletin: Optional[bool] = None
    comments: Optional[str] = None
    # sent by the front-end on PUT, but not used by the from_json method
    id: Optional[int] = None
    updated_at: Optional[str] = None


class EventtypeRequestModel(BaseValidationModel):
    item: EventtypeValidationModel


class PotentialViolationValidationModel(StrictValidationModel):
    title: str = Field(min_length=1)
    title_tr: Optional[str] = None
    # sent by the front-end on PUT, but not used by the from_json method
    title_ar: Optional[str] = None
    id: Optional[int] = None
    updated_at: Optional[str] = None


class PotentialViolationRequestModel(BaseValidationModel):
    item: PotentialViolationValidationModel


class ClaimedViolationValidationModel(StrictValidationModel):
    title: str = Field(min_length=1)
    title_tr: Optional[str] = None
    # sent by the front-end on PUT, but not used by the from_json method
    title_ar: Optional[str] = None
    id: Optional[int] = None
    updated_at: Optional[str] = None


class ClaimedViolationRequestModel(BaseValidationModel):
    item: ClaimedViolationValidationModel


class SourceValidationModel(StrictValidationModel):
    title: str = Field(min_length=1)
    title_ar: Optional[str] = None
    comments: Optional[str] = None
    comments_ar: Optional[str] = None
    parent: Optional[PartialSourceModel] = None
    # sent by the front-end on PUT, but not used by the from_json method
    id: Optional[int] = None
    updated_at: Optional[str] = None
    etl_id: Optional[str] = None


class SourceRequestModel(BaseValidationModel):
    item: SourceValidationModel


class AdminLevelModel(BaseValidationModel):
    id: int
    code: int
    title: str = Field(min_length=1)


class LatLngModel(BaseValidationModel):
    lat: float
    lng: float


class LocationTypeModel(BaseValidationModel):
    id: int
    title: str = Field(min_length=1)
    description: Optional[SanitizedField] = None


class LocationValidationModel(one_must_exist(["title", "title_ar"])):
    title: Optional[str] = None
    title_ar: Optional[str] = None
    description: Optional[SanitizedField] = None
    parent: Optional[PartialLocationModel] = None
    country: Optional[dict] = None
    postal_code: Optional[str] = None
    latlng: Optional[LatLngModel] = None
    location_type: Optional[LocationTypeModel] = None
    admin_level: Optional[AdminLevelModel | str] = (
        None  # if the location_type is POI, front end sends an empty str for admin_level
    )

    # sent by the front-end on PUT, but not used by the from_json method
    id: Optional[int] = None
    updated_at: Optional[str] = None
    tags: Optional[list[str]] = Field(default_factory=list)
    lat: Optional[float] = None
    lng: Optional[float] = None
    full_location: Optional[str] = None
    full_string: Optional[str] = None
    ctitle: Optional[str] = None

    @field_validator("admin_level")
    @classmethod
    def check_admin_level(cls, v: Any, info: ValidationInfo) -> Any:
        """
        Validates the 'admin_level' field if location_type is AdminLevel.

        Args:
            - v: The value of the 'admin_level' field.
            - info: ValidationInfo object containing the current fields being validated.

        Raises:
            - ValueError: If 'admin_level' is not a valid AdminLevelModel or if it is not provided.

        Returns:
            - The validated value of 'admin_level'.
        """
        location_type = info.data.get("location_type")
        if location_type and location_type.title == "Administrative Location":
            if isinstance(v, str):
                raise ValueError("admin_level must be a valid AdminLevelModel, not str")
            if v is None:
                raise ValueError("admin_level must be provided")
        return v


LocationValidationModel.model_rebuild()


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
    lvl: Optional[int] = None
    title: Optional[str] = None
    tsv: Optional[str] = None
    latlng: Optional[LatLngRadiusModel] = None
    location_type: Optional[PartialLocationTypeModel] = None
    admin_level: Optional[PartialAdminLevelModel] = None
    country: Optional[PartialCountryModel] = None
    tags: Optional[str] = None
    optags: Optional[bool] = None


class OptionsModel(BaseValidationModel):
    page: Optional[int] = None
    itemsPerPage: Optional[int] = None


class LocationQueryRequestModel(BaseValidationModel):
    q: LocationQueryValidationModel
    options: OptionsModel


class LocationAdminLevelValidationModel(StrictValidationModel):
    title: str = Field(min_length=1)
    code: int
    display_order: Optional[int] = None
    id: Optional[int] = None


class LocationAdminLevelReorderRequestModel(BaseValidationModel):
    order: list[int]


class LocationAdminLevelRequestModel(BaseValidationModel):
    item: LocationAdminLevelValidationModel


class LocationTypeValidationModel(StrictValidationModel):
    title: str = Field(min_length=1)
    # sent by the front-end on PUT, but not used by the from_json method
    id: Optional[int] = None
    description: Optional[SanitizedField] = None


class LocationTypeRequestModel(BaseValidationModel):
    item: LocationTypeValidationModel


class CountryValidationModel(StrictValidationModel):
    title: str = Field(min_length=1)
    title_tr: Optional[str] = None
    # sent by the front-end on PUT, but not used by the from_json method
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CountryRequestModel(BaseValidationModel):
    item: CountryValidationModel


class ComponentDataMixinValidationModel(BaseValidationModel):
    id: Optional[int] = None
    title: str = Field(min_length=1)
    title_tr: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    deleted: Optional[bool] = None


class ComponentDataMixinRequestModel(BaseValidationModel):
    item: ComponentDataMixinValidationModel


class AtoaInfoValidationModel(StrictValidationModel):
    title: str = Field(min_length=1)
    reverse_title: str = Field(min_length=1)
    title_tr: Optional[str] = None
    reverse_title_tr: Optional[str] = None
    id: Optional[int] = None


class AtoaInfoRequestModel(BaseValidationModel):
    item: AtoaInfoValidationModel


class AtobInfoValidationModel(StrictValidationModel):
    title: str = Field(min_length=1)
    title_tr: Optional[str] = None
    id: Optional[int] = None
    reverse_title: Optional[str] = None
    reverse_title_tr: Optional[str] = None


class AtobInfoRequestModel(BaseValidationModel):
    item: AtobInfoValidationModel


class BtobInfoValidationModel(StrictValidationModel):
    title: str = Field(min_length=1)
    title_tr: Optional[str] = None
    id: Optional[int] = None
    reverse_title: Optional[str] = None
    reverse_title_tr: Optional[str] = None


class BtobInfoRequestModel(BaseValidationModel):
    item: BtobInfoValidationModel


class ItoaInfoValidationModel(StrictValidationModel):
    title: str = Field(min_length=1)
    title_tr: Optional[str] = None
    id: Optional[int] = None
    reverse_title: Optional[str] = None
    reverse_title_tr: Optional[str] = None


class ItoaInfoRequestModel(BaseValidationModel):
    item: ItoaInfoValidationModel


class ItobInfoValidationModel(StrictValidationModel):
    title: str = Field(min_length=1)
    title_tr: Optional[str] = None
    id: Optional[int] = None
    reverse_title: Optional[str] = None
    reverse_title_tr: Optional[str] = None


class ItobInfoRequestModel(BaseValidationModel):
    item: ItobInfoValidationModel


class ItoiInfoValidationModel(StrictValidationModel):
    title: str = Field(min_length=1)
    title_tr: Optional[str] = None
    id: Optional[int] = None
    reverse_title: Optional[str] = None
    reverse_title_tr: Optional[str] = None


class ItoiInfoRequestModel(BaseValidationModel):
    item: ItoiInfoValidationModel


class MediaCategoryValidationModel(StrictValidationModel):
    title: str = Field(min_length=1)
    title_tr: Optional[str] = None
    # sent by the front-end on PUT, but not used by the from_json method
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MediaCategoryRequestModel(BaseValidationModel):
    item: MediaCategoryValidationModel


class GeoLocationTypeValidationModel(StrictValidationModel):
    title: str = Field(min_length=1)
    title_tr: Optional[str] = None
    # sent by the front-end on PUT, but not used by the from_json method
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class GeoLocationTypeRequestModel(BaseValidationModel):
    item: GeoLocationTypeValidationModel


class PartialEventTypeModel(BaseValidationModel):
    id: int


class QueryBaseModel(StrictValidationModel):
    tsv: Optional[str] = None
    extsv: Optional[str] = None
    labels: Optional[list[PartialLabelModel]] = Field(default_factory=list)
    oplabels: Optional[bool] = None
    exlabels: Optional[list[PartialLabelModel]] = Field(default_factory=list)
    opvlabels: Optional[bool] = None
    vlabels: Optional[list[PartialLabelModel]] = Field(default_factory=list)
    exvlabels: Optional[list[PartialLabelModel]] = Field(default_factory=list)
    opsources: Optional[bool] = None
    sources: Optional[list[PartialSourceModel]] = Field(default_factory=list)
    exsources: Optional[list[PartialSourceModel]] = Field(default_factory=list)
    locations: Optional[list[PartialLocationModel]] = Field(default_factory=list)
    oplocations: Optional[bool] = None
    exlocations: Optional[list[PartialLocationModel]] = Field(default_factory=list)
    created: Optional[list[str]] = Field(default_factory=list)
    updated: Optional[list[str]] = Field(default_factory=list)
    docdate: Optional[list[str]] = Field(default_factory=list)
    pubdate: Optional[list[str]] = Field(default_factory=list)
    singleEvent: Optional[bool] = None
    edate: Optional[list[str]] = Field(default_factory=list)
    etype: Optional[PartialEventTypeModel] = None
    elocation: Optional[PartialLocationModel] = None
    roles: Optional[list[int]] = Field(default_factory=list)
    norole: Optional[bool] = None
    assigned: Optional[list[int]] = Field(default_factory=list)
    fpr: Optional[list[int]] = Field(default_factory=list)
    unassigned: Optional[bool] = None
    reviewer: Optional[list[int]] = Field(default_factory=list)
    statuses: Optional[list[str]] = Field(default_factory=list)
    reviewAction: Optional[str] = None
    rel_to_bulletin: Optional[int] = None
    rel_to_actor: Optional[int] = None
    rel_to_incident: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def check_legacy_fields(cls, data: dict) -> dict:
        """
        Checks the legacy date and status fields, throws an error if they are present.

        Args:
            data: The input data dictionary to be validated.

        Raises:
            ValueError: If any of the legacy fields are present in the input data.

        Returns:
            The validated data dictionary.
        """
        old_fields = ["createdwithin", "updatedwithin", "docdatewithin", "pubdatewithin", "status"]
        for field in old_fields:
            if field in data:
                raise ValueError(
                    "The query sent is incompatible with this version. Please delete and re-create the query."
                )
        return data

    @field_validator("updated", "created", "docdate", "pubdate", "edate")
    def validate_date(cls, v):
        """
        Validates the date fields.

        Returns:
            list[str]: The validated list of date values.

        Raises:
            ValueError: If any date in the list is not a valid date.
        """
        if v:
            for date in v:
                try:
                    parse(date)
                except ValueError:
                    raise ValueError(f"Invalid date format: {date}")
        return v


class BulletinQueryLocTypes(Enum):
    LOCATIONS = "locations"
    GEMOARKERS = "geomarkers"
    EVENTS = "events"


class BulletinQueryValidationModel(QueryBaseModel):
    op: Optional[str] = "or"
    ids: list[int] = Field(default_factory=list)
    originid: Optional[str] = None
    tags: Optional[list[str]] = Field(default_factory=list)
    inExact: Optional[bool] = False
    opTags: Optional[bool] = False
    exTags: Optional[list[str]] = Field(default_factory=list)
    exExact: Optional[bool] = False
    opExTags: Optional[bool] = False
    childlabels: Optional[bool] = False
    childverlabels: Optional[bool] = False
    childsources: Optional[bool] = False
    locTypes: Optional[list[str]] = Field(default_factory=list)
    latlng: Optional[LatLngRadiusModel] = None
    # Minimal, permissive container for dynamic-field filters
    # Example item: {"name": "case_number", "op": "contains", "value": "2024-"}
    dyn: Optional[list[dict]] = Field(default_factory=list)

    @field_validator("tags")
    def validate_tags(cls, v):
        """
        Validates the tags field.

        Returns:
            list<str>: The validated tags value.
        """
        if isinstance(v, str):
            v = [v]
        return v


class BulletinQueryRequestModel(BaseValidationModel):
    q: list[BulletinQueryValidationModel] = Field(default_factory=list)
    per_page: int = Field(ge=1, default=PER_PAGE)
    cursor: Optional[str] = None
    include_count: Optional[bool] = False

    @field_validator("per_page")
    def validate_per_page(cls, v):
        valid_values = [int(x) for x in Config.get("ITEMS_PER_PAGE_OPTIONS")]
        if v not in valid_values:
            raise ValueError(f"Invalid per_page value: {v}. Valid values are: {valid_values}")
        return v


class EntityReviewValidationModel(BaseValidationModel):
    review: Optional[SanitizedField] = None
    review_action: Optional[str] = None


class BulletinReviewValidationModel(EntityReviewValidationModel):
    revTags: list[str] = Field(default_factory=list)


class BulletinReviewRequestModel(BaseValidationModel):
    item: BulletinReviewValidationModel


class GenericBulkModel(BaseValidationModel):
    status: Optional[str] = None
    assigned_to_id: Optional[int] = None
    first_peer_reviewer_id: Optional[int] = None
    comments: Optional[str] = None
    roles: list[PartialRoleModel] = Field(default_factory=list)
    rolesReplace: Optional[bool] = None
    assigneeClear: Optional[bool] = None
    reviewerClear: Optional[bool] = None


class BulletinBulkModel(GenericBulkModel):
    tags: list[str] = Field(default_factory=list)
    tagsReplace: Optional[bool] = None


class ActorBulkModel(GenericBulkModel):
    tags: list[str] = Field(default_factory=list)
    tagsReplace: Optional[bool] = None


class IncidentBulkModel(GenericBulkModel):
    assignRelated: Optional[bool] = None
    restrictRelated: Optional[bool] = None


class IncidentBulkUpdateRequestModel(BaseValidationModel):
    items: list[int] = Field(default_factory=list)
    bulk: IncidentBulkModel


class BulletinBulkUpdateRequestModel(BaseValidationModel):
    items: list[int] = Field(default_factory=list)
    bulk: BulletinBulkModel


class ActorBulkUpdateRequestModel(BaseValidationModel):
    items: list[int] = Field(default_factory=list)
    bulk: ActorBulkModel


class BulkUpdateRequestModel(BaseValidationModel):
    items: list[int] = Field(default_factory=list)
    bulk: GenericBulkModel


class GenericSelfAssignValidationModel(BaseValidationModel):
    comments: Optional[str] = None


class BulletinSelfAssignValidationModel(GenericSelfAssignValidationModel):
    tags: list[str] = Field(default_factory=list)


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
    ids: list[int] = Field(default_factory=list)
    originid: Optional[str] = None
    nickname: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    tags: Optional[list[str]] = Field(default_factory=list)
    inExact: Optional[bool] = False
    opTags: Optional[bool] = False
    exTags: Optional[list[str]] = Field(default_factory=list)
    exExact: Optional[bool] = False
    opExTags: Optional[bool] = False
    opEthno: Optional[bool] = None
    ethnography: list[PartialEthnographyModel] = Field(default_factory=list)
    opNat: Optional[bool] = None
    nationality: list[PartialNationalityModel] = Field(default_factory=list)
    resLocations: list[PartialLocationModel] = Field(default_factory=list)
    originLocations: list[PartialLocationModel] = Field(default_factory=list)
    exResLocations: list[PartialLocationModel] = Field(default_factory=list)
    exOriginLocations: list[PartialLocationModel] = Field(default_factory=list)
    occupation: Optional[str] = None
    position: Optional[str] = None
    opDialects: Optional[bool] = None
    dialects: list[PartialDialectModel] = Field(default_factory=list)
    family_status: Optional[str] = None
    sex: Optional[str] = None
    age: Optional[str] = None
    civilian: Optional[str] = None
    type_: Optional[str] = Field(default=None, alias="type")
    id_number: Optional[dict[str, str]] = None
    locTypes: list[str] = Field(default_factory=list)
    latlng: Optional[LatLngRadiusModel] = None
    childlabels: Optional[bool] = False
    childverlabels: Optional[bool] = False
    childsources: Optional[bool] = False
    # Minimal, permissive container for dynamic-field filters
    # Example item: {"name": "field_name", "op": "contains", "value": "test"}
    dyn: Optional[list[dict]] = Field(default_factory=list)

    @field_validator("tags")
    def validate_tags(cls, v):
        """
        Validates the tags field.

        Returns:
            list<str>: The validated tags value.
        """
        if isinstance(v, str):
            v = [v]
        return v


class ActorQueryRequestModel(BaseValidationModel):
    q: list[ActorQueryModel] = Field(default_factory=list)
    per_page: int = Field(default=PER_PAGE, ge=1)
    cursor: Optional[str] = None
    include_count: Optional[bool] = False

    @field_validator("per_page")
    def validate_per_page(cls, v):
        valid_values = [int(x) for x in Config.get("ITEMS_PER_PAGE_OPTIONS")]
        if v not in valid_values:
            raise ValueError(f"Invalid per_page value: {v}. Valid values are: {valid_values}")
        return v


class ActorReviewRequestModel(BaseValidationModel):
    item: EntityReviewValidationModel


class UserValidationModel(StrictValidationModel):
    email: Optional[str] = None
    username: str = Field(min_length=4, max_length=32)
    password: Optional[str] = None  # Optional on PUT, required on POST
    name: str = Field(min_length=1)
    roles: list[PartialRoleModel] = Field(default_factory=list)
    view_usernames: Optional[bool] = None
    view_full_history: Optional[bool] = None
    view_simple_history: Optional[bool] = None
    can_self_assign: Optional[bool] = None
    can_edit_locations: Optional[bool] = None
    can_export: Optional[bool] = None
    can_import_web: Optional[bool] = None
    active: bool
    force_reset: Optional[str] = None
    google_id: Optional[str] = None
    id: Optional[int] = None
    two_factor_devices: Optional[Any] = None

    @field_validator("username", mode="before")
    @classmethod
    def validate_username(cls, v: str) -> str:
        return validate_username_constraints(v)

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, v: Optional[str]) -> Optional[str]:
        """
        Validates the email format and returns the validated email.

        Args:
            v: The email to validate

        Returns:
            Optional[str]: The validated email or None

        Raises:
            ValueError: If the email format is invalid
        """
        if not v:
            return v

        try:
            v = validate_email_format(v)
        except ValidationError:
            raise ValueError("Invalid email format")

        if Config.get("MAIL_ALLOWED_DOMAINS") and "*" not in Config.get("MAIL_ALLOWED_DOMAINS"):
            if v.domain not in Config.get("MAIL_ALLOWED_DOMAINS"):
                raise ValueError(
                    f"Email domain is not allowed. Allowed domains are: {', '.join(Config.get('MAIL_ALLOWED_DOMAINS'))}"
                )

        return v.normalized

    @field_validator("password")
    def validate_password(cls, v):
        if not v:
            return v
        return validate_password_policy(v)


class UserRequestModel(BaseValidationModel):
    item: UserValidationModel


class UserNameCheckValidationModel(BaseValidationModel):
    item: str = Field(min_length=4, max_length=32)

    @field_validator("item", mode="before")
    @classmethod
    def validate_username_check(cls, v: str) -> str:
        if not v:
            raise ValueError("Username cannot be empty")
        return validate_username_constraints(v)


class UserPasswordCheckValidationModel(BaseValidationModel):
    password: str  # no assumptions about password policy here, let field validator do the job

    @field_validator("password")
    def validate_password(cls, v):
        return validate_password_policy(v)


class UserForceResetRequestModel(BaseValidationModel):
    item: PartialUserModel


class RoleValidationModel(BaseValidationModel):
    name: str = Field(min_length=1)
    description: Optional[str] = None
    color: str = Field(min_length=1)
    id: Optional[int] = None


class RoleRequestModel(BaseValidationModel):
    item: RoleValidationModel


class IncidentQueryModel(QueryBaseModel):
    ids: list[int] = Field(default_factory=list)
    potentialVCats: list[PartialPotentialViolationModel] = Field(default_factory=list)
    claimedVCats: list[PartialClaimedViolationModel] = Field(default_factory=list)
    # Minimal, permissive container for dynamic-field filters
    # Example item: {"name": "field_123", "op": "contains", "value": "test"}
    dyn: Optional[list[dict]] = Field(default_factory=list)


class IncidentQueryRequestModel(BaseValidationModel):
    q: IncidentQueryModel
    per_page: int = Field(default=PER_PAGE, ge=1)
    cursor: Optional[str] = None
    include_count: Optional[bool] = False

    @field_validator("per_page")
    def validate_per_page(cls, v):
        valid_values = [int(x) for x in Config.get("ITEMS_PER_PAGE_OPTIONS")]
        if v not in valid_values:
            raise ValueError(f"Invalid per_page value: {v}. Valid values are: {valid_values}")
        return v


class IncidentReviewRequestModel(BaseValidationModel):
    item: EntityReviewValidationModel


class QueryValidationModel(BaseValidationModel):
    q: dict[str, Any] = Field(default_factory=dict)
    name: Optional[str] = None
    # Optional on PUT, required on POST
    type_: Optional[str] = Field(alias="type", default=None)


class GraphVisualizeRequestModel(BaseValidationModel):
    q: list[dict[str, Any]] | dict[str, Any]


class DefaultMapCenterModel(BaseValidationModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class ActivitiesModel(BaseModel):
    APPROVE: bool = Field(default=False)
    BULK: bool = Field(default=False)
    CREATE: bool = Field(default=False)
    DELETE: bool = Field(default=False)
    DOWNLOAD: bool = Field(default=False)
    LOGIN: bool = Field(default=False)
    LOGOUT: bool = Field(default=False)
    REJECT: bool = Field(default=False)
    REQUEST: bool = Field(default=False)
    REVIEW: bool = Field(default=False)
    SEARCH: bool = Field(default=False)
    SELF_ASSIGN: bool = Field(default=False, alias="SELF-ASSIGN")
    UPDATE: bool = Field(default=False)
    UPLOAD: bool = Field(default=False)
    VIEW: bool = Field(default=False)


class NotificationConfigModel(BaseValidationModel):
    email_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    category: Optional[str] = None


class ConfigValidationModel(StrictValidationModel):
    SECURITY_TWO_FACTOR_REQUIRED: bool
    SECURITY_PASSWORD_LENGTH_MIN: int = Field(ge=8)
    SECURITY_ZXCVBN_MINIMUM_SCORE: int = Field(ge=0, le=4)
    SESSION_RETENTION_PERIOD: int = Field(ge=0)
    FILESYSTEM_LOCAL: bool
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    S3_BUCKET: Optional[str] = None
    AWS_REGION: Optional[str] = None
    ACCESS_CONTROL_RESTRICTIVE: bool
    AC_USERS_CAN_RESTRICT_NEW: bool
    ETL_TOOL: bool
    SHEET_IMPORT: bool
    BABEL_DEFAULT_LOCALE: str
    GOOGLE_MAPS_API_KEY: Optional[str] = None
    GEO_MAP_DEFAULT_CENTER: DefaultMapCenterModel
    EXPORT_TOOL: bool
    EXPORT_DEFAULT_EXPIRY: int = Field(gt=0)
    ACTIVITIES_RETENTION: int = Field(gt=0)
    WEB_IMPORT: bool

    @field_validator("MAPS_API_ENDPOINT", "GOOGLE_DISCOVERY_URL", mode="before", check_fields=False)
    @classmethod
    def validate_urls(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Invalid value for MAPS_API_ENDPOINT or GOOGLE_DISCOVERY_URL")
        try:
            HttpUrl(v)
        except ValueError:
            raise ValueError(f"Invalid URL: {v}")
        return v

    @field_validator(
        "MEDIA_ALLOWED_EXTENSIONS",
        "SHEETS_ALLOWED_EXTENSIONS",
        "ETL_VID_EXT",
        "OCR_EXT",
        check_fields=False,
    )
    @classmethod
    def validate_allowed_extensions(cls, v):
        if v:
            for ext in v:
                if not isinstance(ext, str):
                    raise ValueError(
                        "MEDIA_ALLOWED_EXTENSIONS and SHEETS_ALLOWED_EXTENSIONS must be lists of strings"
                    )
                if len(ext) < 2 or len(ext) > 4:
                    raise ValueError(
                        "Invalid value for MEDIA_ALLOWED_EXTENSIONS or SHEETS_ALLOWED_EXTENSIONS"
                    )
        return v

    @field_validator("BABEL_DEFAULT_LOCALE")
    @classmethod
    def validate_default_locale(cls, v):
        if v and not re.match(r"^[a-z]{2}$", v.lower()):
            raise ValueError("Invalid value for BABEL_DEFAULT_LOCALE")
        return v

    @field_validator("GOOGLE_MAPS_API_KEY")
    @classmethod
    def validate_google_maps_key(cls, v):
        if not v:
            return None
        if not isinstance(v, str):
            raise ValueError("Invalid value for GOOGLE_MAPS_API_KEY")
        # Allow masked value (user not changing secret)
        if v == ConfigManager.MASK_STRING:
            return v
        if len(v) < 30 or len(v) > 60:
            raise ValueError("Invalid value for GOOGLE_MAPS_API_KEY")
        return v

    def validate_recaptcha_key(v):
        if not isinstance(v, str):
            return None
        # Allow masked value (user not changing secret)
        if v == ConfigManager.MASK_STRING:
            return v
        if len(v) < 20 or len(v) > 50:
            return None
        return v

    def validate_google_key(v):
        if not isinstance(v, str):
            return None
        # Allow masked value (user not changing secret)
        if v == ConfigManager.MASK_STRING:
            return v
        if len(v) < 20 or len(v) > 100:
            return None
        return v

    def validate_aws_access_key(v):
        if not isinstance(v, str):
            return None
        if len(v) < 16 or len(v) > 64:
            return None
        return v

    def validate_aws_secret_key(v):
        if not isinstance(v, str):
            return None
        # Allow MASK String as a valid value
        if v == "**********":
            return v
        if len(v) < 40 or len(v) > 64:
            return None
        return v

    def validate_s3_bucket(v):
        if not isinstance(v, str):
            return None

        # Check length
        if len(v) < 3 or len(v) > 63:
            return None

        # Check for valid characters
        if not re.match(r"^[a-z0-9][a-z0-9.\-]{1,61}[a-z0-9]$", v):
            return None

        # Check for adjacent periods
        if ".." in v:
            return None

        # Check if formatted as IP address
        if re.match(r"\d+\.\d+\.\d+\.\d+", v):
            return None

        # Check for forbidden prefixes
        forbidden_prefixes = ["xn--", "sthree-", "sthree-configurator", "amzn-s3-demo-"]
        if any(v.startswith(prefix) for prefix in forbidden_prefixes):
            return None

        # Check for forbidden suffixes
        forbidden_suffixes = ["-s3alias", "--ol-s3", ".mrap", "--x-s3"]
        if any(v.endswith(suffix) for suffix in forbidden_suffixes):
            return None

        return v

    def validate_aws_region(v):
        if not isinstance(v, str):
            return None

        valid_regions = {
            "us-east-2",
            "us-east-1",
            "us-west-1",
            "us-west-2",
            "af-south-1",
            "ap-east-1",
            "ap-south-2",
            "ap-southeast-3",
            "ap-southeast-4",
            "ap-south-1",
            "ap-northeast-3",
            "ap-northeast-2",
            "ap-southeast-1",
            "ap-southeast-2",
            "ap-northeast-1",
            "ca-central-1",
            "ca-west-1",
            "eu-central-1",
            "eu-west-1",
            "eu-west-2",
            "eu-south-1",
            "eu-west-3",
            "eu-south-2",
            "eu-north-1",
            "eu-central-2",
            "il-central-1",
            "me-south-1",
            "me-central-1",
            "sa-east-1",
            "us-gov-east-1",
            "us-gov-west-1",
        }

        if v not in valid_regions:
            return None

        return v

    @model_validator(mode="before")
    @classmethod
    def validate_rules(cls, values):
        if values.get("RECAPTCHA_ENABLED") and not (
            values.get("RECAPTCHA_PUBLIC_KEY")
            and cls.validate_recaptcha_key(values.get("RECAPTCHA_PUBLIC_KEY"))
        ):
            raise ValueError(
                "RECAPTCHA_PUBLIC_KEY must be provided and valid if RECAPTCHA_ENABLED is True"
            )
        if values.get("RECAPTCHA_ENABLED") and not (
            values.get("RECAPTCHA_PRIVATE_KEY")
            and cls.validate_recaptcha_key(values.get("RECAPTCHA_PRIVATE_KEY"))
        ):
            raise ValueError(
                "RECAPTCHA_PRIVATE_KEY must be provided and valid if RECAPTCHA_ENABLED is True"
            )
        if values.get("GOOGLE_OAUTH_ENABLED") and not (
            values.get("GOOGLE_CLIENT_ID")
            and cls.validate_google_key(values.get("GOOGLE_CLIENT_ID"))
        ):
            raise ValueError(
                "GOOGLE_CLIENT_ID must be provided and valid if GOOGLE_OAUTH_ENABLED is True"
            )
        if values.get("GOOGLE_OAUTH_ENABLED") and not (
            values.get("GOOGLE_CLIENT_SECRET")
            and cls.validate_google_key(values.get("GOOGLE_CLIENT_SECRET"))
        ):
            raise ValueError(
                "GOOGLE_CLIENT_SECRET must be provided and valid if GOOGLE_OAUTH_ENABLED is True"
            )

        if not bool(values.get("FILESYSTEM_LOCAL")) and not (
            values.get("AWS_ACCESS_KEY_ID")
            and cls.validate_aws_access_key(values.get("AWS_ACCESS_KEY_ID"))
            and values.get("AWS_SECRET_ACCESS_KEY")
            and cls.validate_aws_secret_key(values.get("AWS_SECRET_ACCESS_KEY"))
            and values.get("S3_BUCKET")
            and cls.validate_s3_bucket(values.get("S3_BUCKET"))
            and values.get("AWS_REGION")
            and cls.validate_aws_region(values.get("AWS_REGION"))
        ):
            raise ValueError(
                "AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET and AWS_REGION must be provided if FILESYSTEM_LOCAL is False"
            )

        if (
            values.get("DEDUP_LOW_DISTANCE")
            and values.get("DEDUP_MAX_DISTANCE")
            and values.get("DEDUP_LOW_DISTANCE") > values.get("DEDUP_MAX_DISTANCE")
        ):
            raise ValueError("DEDUP_LOW_DISTANCE must be less than or equal to DEDUP_MAX_DISTANCE")
        return values


class FullConfigValidationModel(ConfigValidationModel):
    SECURITY_FRESHNESS: int = Field(gt=0)
    SECURITY_FRESHNESS_GRACE_PERIOD: int = Field(ge=0)
    DISABLE_MULTIPLE_SESSIONS: bool
    RECAPTCHA_ENABLED: bool
    RECAPTCHA_PUBLIC_KEY: Optional[str] = None
    RECAPTCHA_PRIVATE_KEY: Optional[str] = None
    GOOGLE_OAUTH_ENABLED: bool
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_DISCOVERY_URL: str
    MEDIA_ALLOWED_EXTENSIONS: list[str] = Field(default_factory=list)
    MEDIA_UPLOAD_MAX_FILE_SIZE: float = Field(gt=0)
    SHEETS_ALLOWED_EXTENSIONS: list[str] = Field(default_factory=list)
    ETL_PATH_IMPORT: bool
    ETL_VID_EXT: list[str] = Field(default_factory=list)
    OCR_ENABLED: bool
    OCR_EXT: list[str] = Field(default_factory=list)
    DEDUP_TOOL: bool
    MAPS_API_ENDPOINT: str
    DEDUP_LOW_DISTANCE: Optional[float] = Field(default=None, ge=0, le=1)
    DEDUP_MAX_DISTANCE: Optional[float] = Field(default=None, ge=0, le=1)
    DEDUP_BATCH_SIZE: Optional[int] = Field(default=None, gt=0)
    DEDUP_INTERVAL: Optional[int] = Field(default=None, gt=0)
    ITEMS_PER_PAGE_OPTIONS: list[int] = Field(default_factory=list)
    VIDEO_RATES: list[float] = Field(default_factory=list)
    ACTIVITIES: ActivitiesModel
    ADV_ANALYSIS: bool
    SETUP_COMPLETE: bool = Field(default=True)
    LOCATIONS_INCLUDE_POSTAL_CODE: bool
    MAIL_ENABLED: bool
    MAIL_ALLOWED_DOMAINS: list[str] = Field(default_factory=list)
    MAIL_SERVER: Optional[str] = None
    MAIL_PORT: Optional[int] = None
    MAIL_USE_TLS: Optional[bool] = None
    MAIL_USE_SSL: Optional[bool] = None
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_DEFAULT_SENDER: Optional[str] = None
    TRANSCRIPTION_ENABLED: bool
    WHISPER_MODEL: Optional[str] = None
    YTDLP_PROXY: Optional[str] = None
    YTDLP_ALLOWED_DOMAINS: list[str] = Field(default_factory=list)
    YTDLP_COOKIES: Optional[str] = None
    NOTIFICATIONS: dict[str, NotificationConfigModel] = Field(default_factory=dict)

    @model_validator(mode="before")
    def ensure_setup_complete(cls, values):
        values["SETUP_COMPLETE"] = True
        return values

    @model_validator(mode="before")
    def validate_mail_settings(cls, values):
        if values.get("MAIL_ENABLED"):
            mail_password = values.get("MAIL_PASSWORD")
            if (
                not values.get("MAIL_SERVER")
                or not values.get("MAIL_PORT")
                or not values.get("MAIL_USERNAME")
                or not (
                    mail_password
                    and (mail_password == ConfigManager.MASK_STRING or len(mail_password) > 0)
                )
                or not values.get("MAIL_DEFAULT_SENDER")
            ):
                raise ValueError(
                    "MAIL_SERVER, MAIL_PORT, MAIL_USERNAME and MAIL_PASSWORD must be provided if MAIL_ENABLED is True"
                )
            if not values.get("MAIL_ALLOWED_DOMAINS"):
                raise ValueError(
                    "MAIL_ALLOWED_DOMAINS must be provided and not empty if MAIL_ENABLED is True"
                )
        return values

    @model_validator(mode="before")
    def validate_whisper_model(cls, values):
        if values.get("TRANSCRIPTION_ENABLED"):
            if not values.get("WHISPER_MODEL"):
                raise ValueError("WHISPER_MODEL must be provided if TRANSCRIPTION_ENABLED is True")
            if values.get("WHISPER_MODEL") and values.get("WHISPER_MODEL") not in [
                model["model_name"] for model in Constants.WHISPER_MODEL_OPTS
            ]:
                raise ValueError("Invalid Whisper Model")
        return values

    @field_validator("ITEMS_PER_PAGE_OPTIONS")
    @classmethod
    def validate_page_options(cls, v: list[int]) -> list[int]:
        if not all(x > 0 for x in v):
            raise ValueError("All items per page options must be greater than 0")
        return v

    @field_validator("VIDEO_RATES")
    @classmethod
    def validate_video_rates(cls, v: list[float]) -> list[float]:
        if not all(x > 0 for x in v):
            raise ValueError("All video rates must be greater than 0")
        return v

    @field_validator("YTDLP_PROXY")
    @classmethod
    def validate_proxy_url(cls, v: Optional[str]) -> Optional[str]:
        """Validates the proxy URL format."""
        if not v:
            return None

        valid_schemes = {"http", "https", "socks4", "socks5", "socks5h"}
        try:
            parsed = urlparse(v)
            if parsed.scheme not in valid_schemes:
                raise ValueError(f"Proxy URL must start with one of: {', '.join(valid_schemes)}")
            if not parsed.netloc:
                raise ValueError("Invalid proxy URL format")
            # Check if port is provided
            if ":" not in parsed.netloc.split("@")[-1]:
                raise ValueError("Proxy URL must include port number")
            return v
        except Exception:
            raise ValueError("Invalid proxy URL format")

    @field_validator("YTDLP_ALLOWED_DOMAINS")
    @classmethod
    def validate_domains(cls, v: list[str]) -> list[str]:
        """Validates domain format."""
        if not v:
            return []

        for domain in v:
            if not re.match(r"^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$", domain):
                raise ValueError(f"Invalid domain format: {domain}")
        return v

    @field_validator("YTDLP_COOKIES")
    @classmethod
    def validate_cookies(cls, v: Optional[str]) -> Optional[str]:
        """Validates the cookies data format."""
        if not v:
            return None

        # Basic validation that it looks like cookie data
        lines = v.splitlines()
        for line in lines:
            if line.strip() and not line.startswith("#"):  # Skip empty lines and comments
                # Check if line has minimum required tab-separated fields
                fields = line.split("\t")
                if len(fields) < 6:
                    raise ValueError(
                        "Invalid cookie format. Each line should have domain, flag, path, secure, expiry, name, value"
                    )
        return v


class ConfigRequestModel(BaseValidationModel):
    conf: FullConfigValidationModel


class WizardConfigRequestModel(BaseValidationModel):
    conf: ConfigValidationModel


class WebImportValidationModel(StrictValidationModel):
    url: HttpUrl

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: HttpUrl) -> str:
        """
        Validates the URL for web import.

        Args:
            - v: The URL to validate.

        Raises:
            - ValueError: If the domain is not allowed.

        Returns:
            - The validated URL.
        """
        # Check domain restrictions
        domain = v._url.host
        if domain.startswith("www."):
            domain = domain[4:]
        allowed_domains = Config.get("YTDLP_ALLOWED_DOMAINS")
        if not any(domain.endswith(allowed) for allowed in allowed_domains):
            raise ValueError(f"Imports not allowed from {domain}")

        return str(v)


# Dynamic Field Validation Models
class DynamicFieldBulkSaveModel(StrictValidationModel):
    """Validation for bulk save operations."""

    entity_type: str
    changes: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        """Validate entity_type is one of the allowed values."""
        allowed = ["bulletin", "actor", "incident"]
        if v not in allowed:
            raise ValueError(f"entity_type must be one of: {', '.join(allowed)}")
        return v


class ActivityQueryValidationModel(StrictValidationModel):
    user: Optional[int] = None
    action: Optional[str] = None
    model: Optional[str] = None
    created: Optional[List[str]] = None

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: Optional[str]) -> Optional[str]:
        """Validate action is among allowed values."""
        if v is None:
            return v
        allowed = Activity.get_action_values()
        if v not in allowed:
            raise ValueError(f"Invalid action: {v}. Allowed actions are: {', '.join(allowed)}")
        return v

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: Optional[str]) -> Optional[str]:
        """Validate model is among allowed values."""
        if v is None:
            return v
        allowed = [
            "bulletin",
            "actor",
            "incident",
            "user",
            "role",
            "location",
            "source",
            "label",
            "media",
            "eventtype",
            "dynamic_field_bulk",
            "config",
        ]
        if v not in allowed:
            raise ValueError(f"Invalid model: {v}. Allowed models are: {', '.join(allowed)}")
        return v

    @field_validator("created")
    @classmethod
    def validate_created(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate created contains valid dates."""
        if v:
            for date_str in v:
                try:
                    parse(date_str)
                except ValueError:
                    raise ValueError(f"Invalid date format in created: {date_str}")
        return v


class ActivityQueryRequestModel(StrictValidationModel):
    q: ActivityQueryValidationModel
    options: OptionsModel
