import re
import time
from typing import Any, Iterable, Optional, Union

import pandas as pd
import gettext
from sqlalchemy.orm.attributes import flag_modified

from enferno.admin.models import (
    Actor,
    ActorProfile,
    Event,
    Eventtype,
    Location,
    Label,
    Source,
    Country,
    Ethnography,
    Dialect,
    Activity,
)
from enferno.data_import.models import DataImport

from enferno.utils.base import DatabaseException
from enferno.utils.date_helper import DateHelper
from enferno.user.models import Role, User
import enferno.utils.typing as t

# configurations

# add your own strings if needed
boolean_positive = ["y", "yes", "true", "t"]
config_dict = {
    "age": "actorAge",
    "sex": "actorSex",
    "civilian": "actorCivilian",
    "type": "actorTypes",
    "physique": "physique",
    "hair_loss": "hairLoss",
    "hair_type": "hairType",
    "hair_length": "hairLength",
    "hair_color": "hairColor",
    "facial_hair": "facialHair",
    "handedness": "handness",
    "eye_color": "eyeColor",
    "case_status": "caseStatus",
    "smoker": "smoker",
    "pregnant_at_disappearance": "pregnant",
    "glasses": "glasses",
    "skin_markings_opts": "skinMarkings",
}

sec_dict = {
    "labels": {"model": Label, "attr": "labels", "parent": "P"},
    "verLabels": {"model": Label, "attr": "ver_labels", "parent": "P"},
    "sources": {"model": Source, "attr": "sources", "parent": "P"},
    "ethnographies": {"model": Ethnography, "attr": "ethnographies", "parent": "A"},
    "nationalities": {"model": Country, "attr": "nationalities", "parent": "A"},
    "dialects": {"model": Dialect, "attr": "dialects", "parent": "A"},
}

details_list = [
    "seen_in_detention_details",
    "known_dead_details",
    "injured_details",
    "skin_markings_details",
]

opts_list = ["seen_in_detention_opts", "known_dead_opts", "injured_opts"]

bool_list = ["dental_record", "family_notified", "missing_relatives", "source_link_type"]

location_list = ["origin_place"]
date_list = ["documentation_date", "publish_date"]


class SheetImport:
    """Class to import data from a CSV or XLSX file into the database."""

    def __init__(
        self,
        filepath: str,
        sheet: Any,
        row_id: Any,
        data_import_id: t.id,
        map: Any,
        batch_id: Any,
        vmap: Any = None,
        roles: list = [],
        config: Any = None,
        lang: str = "en",
    ):
        self.row = SheetImport.sheet_to_df(filepath, sheet).iloc[row_id]
        self.data_import = DataImport.query.get(data_import_id)
        self.map = map
        self.batch_id = batch_id
        self.vmap = vmap
        self.roles = roles
        self.config = config
        # set sheet language
        self.lang = lang

        self.actor = Actor()
        self.actor.name = "Temp"
        self.actor_profile = ActorProfile()
        self.actor_profile.actor = self.actor
        self.actor.actor_profiles.append(self.actor_profile)
        self.actor_profile.description = ""

        # Install translator based on selected sheet language to be used for matching
        if lang != "en":
            self.translator = gettext.translation(
                "messages", localedir="enferno/translations", languages=[lang]
            )
            self.translator.install()
        else:
            self.translator = None

    @staticmethod
    def parse_csv(filepath: str) -> dict:
        """
        Parses a CSV file and returns the columns and the head of the file.

        Args:
            - filepath: The path to the CSV file.

        Returns:
            - A dictionary containing the columns and the head of the file.
        """
        # read the file partially only for parsing purposes
        df = pd.read_csv(filepath, keep_default_na=False)
        df.dropna(how="all", axis=1, inplace=True)
        df = df.astype(str)

        columns = df.columns.to_list()
        head = df.head().to_dict()

        return {"columns": columns, "head": head}

    @staticmethod
    def parse_excel(filepath: str, sheet: Any) -> dict:
        """
        Parses an Excel file and returns the columns and the head of the file.

        Args:
            - filepath: The path to the Excel file.
            - sheet: The sheet name to parse.

        Returns:
            - A dictionary containing the columns and the head of the file.
        """
        df = pd.read_excel(filepath, sheet_name=sheet)
        df.dropna(how="all", axis=1, inplace=True)
        df = df.astype(str)

        columns = df.columns.to_list()
        # drop nan values before generating head rows
        df.fillna("", inplace=True)
        head = df.head().to_dict()

        return {"columns": columns, "head": head}

    @staticmethod
    def get_sheets(filepath: str) -> list:
        """
        Returns the sheets in an Excel file.

        Args:
            - filepath: The path to the Excel file.

        Returns:
            - A list of the sheet names in the Excel file.
        """
        xls = pd.ExcelFile(filepath)
        return xls.sheet_names

    @staticmethod
    def sheet_to_df(filepath: str, sheet: Optional[list] = None) -> pd.DataFrame:
        """
        Parses CSV or XLSX file.

        Args:
            - filepath: The path to the file.
            - sheet: The sheet name for XLSX files (optional).

        Returns:
            - A DataFrame containing the parsed data.
        """
        if sheet:
            df = pd.read_excel(filepath, sheet_name=sheet, keep_default_na=False)
        else:
            df = pd.read_csv(filepath, keep_default_na=False)

        df.drop_duplicates(inplace=True)
        df.fillna("")

        return df

    @staticmethod
    def parse_array_field(val: str) -> list:
        """
        Static method to handle parsing of array csv columns.

        Args:
            - val: The column to parse.

        Returns:
            - A list of values.
        """
        if "," not in val:
            return [val.strip('"“” ')]
        rex = r"\"[^\"]+\"+|[^ , ]+"
        matches = re.findall(rex, val)
        matches = [match.strip('"“” ') for match in matches]
        return matches

    @staticmethod
    def closest_match(txt: str, lst: list[str]) -> Optional[str]:
        """
        Static method to find the closest match in a list.

        Args:
            - txt: The string to search for.
            - lst: The list of values to pick from.

        Returns:
            - The matching list item in the correct exact case.
        """
        for item in lst:
            if item.lower().strip() == str(txt).lower().strip():
                return item
        return None

    def set_actor_or_profile_attr(self, field: str, value: Any) -> None:
        """
        Method to set actor or actor profile attributes.

        Args:
            - field: The name of the attribute to set.
            - value: The value to set for the attribute.

        """
        if field in ActorProfile.__table__.columns:
            setattr(self.actor_profile, field, value)
        else:
            setattr(self.actor, field, value)

    def set_skin_markings(self, value: str, markings: list, trans: list) -> None:
        """
        Sets the skin markings for the actor profile based on the provided field, value, list, and trans parameters.

        Args:
            - value: The value of the field.
            - markings: The list of available skin markings.
            - trans: The list of translations for the skin markings.

        Returns:
            None
        """
        # check if array is sent
        results = SheetImport.parse_array_field(value)
        results = [x for x in results if x in trans]
        if not self.actor_profile.skin_markings:
            self.actor_profile.skin_markings = {"opts": [], "details": ""}
        self.actor_profile.skin_markings["opts"] = [markings[trans.index(x)] for x in results]
        flag_modified(self.actor_profile, "skin_markings")

    def generate_translations(self, field: str) -> tuple[list[Any], list[str] | list[Any]]:
        """
        Generate translations for a given list field.

        Args:
            - field: The list field for which translations need to be generated.

        Returns:
            - tuple: A tuple containing two lists - restrict and trans.
                - restrict: A list of entries in the configuration dictionary for the given field.
                - trans: A list of translated strings for the entries in the restrict list, if a translator is available.
                         Otherwise, it points to the restrict list itself.
        """
        # create a list from dict of entries in conf
        restrict = [x["en"] for x in self.config.get(config_dict[field])]
        # generate a list of translated strings if lang other than en
        # point to previous list if lang is eng
        trans = [self.translator.gettext(x) for x in restrict] if self.translator else restrict

        return restrict, trans

    def set_from_list(self, field: str, value: str) -> None:
        """
        Method to set single and multi list columns.

        Args:
            - field: The field to set the value for.
            - value: The value to set for the field.

        Returns:
            None
        """
        restrict, trans = self.generate_translations(field)

        if value and restrict:
            # skin markings are special
            # it's a multi select field
            if field == "skin_markings_opts":
                self.set_skin_markings(value, restrict, trans)
            elif result := SheetImport.closest_match(value, trans):
                self.set_actor_or_profile_attr(field, restrict[trans.index(result)])
            else:
                self.handle_mismatch(field, value)

            self.data_import.add_to_log(f"Processed {field}")
        else:
            self.handle_mismatch(field, value)

    def set_opts(self, opts: str, value: str) -> None:
        """
        Method to set option columns.

        Args:
            - opts: The option field to set.
            - value: The value to set for the field.

        Returns:
            None
        """
        field = opts.replace("_opts", "")
        if not str(value).lower().strip() in ["yes", "no", "unknown"]:
            return self.handle_mismatch(field, value)

        attr = getattr(self.actor_profile, field)
        if not attr:
            setattr(self.actor_profile, field, {"opts": "", "details": ""})
        getattr(self.actor_profile, field)["opts"] = str(value).strip().capitalize()
        flag_modified(self.actor_profile, field)
        self.data_import.add_to_log(f"Processed {field}")

    def set_details(self, details: str, value: Any) -> None:
        """
        Method to set details fields.

        Args:
            - details: The details field to set.
            - value: The value to set for the field.

        Returns:
            None
        """
        field = details.replace("_details", "")
        attr = getattr(self.actor_profile, field)
        if not attr:
            if details == "skin_markings_details":
                setattr(self.actor_profile, field, {"opts": [], "details": ""})
            else:
                setattr(self.actor_profile, field, {"opts": "", "details": ""})
        getattr(self.actor_profile, field)["details"] = str(value)
        flag_modified(self.actor_profile, field)
        self.data_import.add_to_log(f"Processed {field}")

    def set_location(self, field: str, value: Any) -> None:
        """
        Method to set location columns.

        Args:
            - field: The location field to set.
            - value: The value to set for the field.

        Returns:
            None
        """
        location = Location.find_by_title(str(value))
        if location:
            setattr(self.actor, field, location)
            self.data_import.add_to_log(f"Processed {field}")
        else:
            self.handle_mismatch(field, value)

    def set_secondaries(self, field: str, value: Any) -> None:
        """
        Method to set Labels and Sources.

        Args:
            - field: The field to set the value for.
            - value: The value to set for the field.

        Returns:
            None
        """
        model = sec_dict[field]["model"]
        attr = sec_dict[field]["attr"]

        items = SheetImport.parse_array_field(value)

        # set to avoid dups
        s = set()
        for item in items:
            x = model.find_by_title(str(item))
            if x:
                s.add(x)
        if s:
            try:
                if sec_dict[field]["parent"] == "A":
                    setattr(self.actor, attr, list(s))
                else:
                    setattr(self.actor_profile, attr, list(s))
                self.data_import.add_to_log(f"Processed {field}")
            except:
                self.handle_mismatch(field, value)

    def set_date(self, field: str, value: str) -> None:
        """
        Method to set date columns.

        Args:
            - field: The date field to set.
            - value: The value to set for the field.

        Returns:
            None
        """
        try:
            setattr(self.actor_profile, field, DateHelper.parse_date(value))
            self.data_import.add_to_log(f"Processed {field}")
        except:
            self.handle_mismatch(field, value)

    def set_bool(self, field: str, value: Any) -> None:
        """
        Method to set boolean columns.

        Args:
            - field: The boolean field to set.
            - value: The value to set for the field.

        Returns:
            None
        """
        try:
            if value.__class__ == str and value.lower() in boolean_positive or value == 1:
                setattr(self.actor_profile, field, True)
            else:
                setattr(self.actor_profile, field, False)
            self.data_import.add_to_log(f"Processed {field}")
        except:
            self.handle_mismatch(field, value)

    def set_tags(self, value: Any) -> None:
        """
        Method to set tags on the actor.

        Args:
            - value: The value to set for the tags field. Can be a comma-separated string or a single value.

        Returns:
            None
        """
        if not value:
            return

        # Parse the value into a list of tags
        if isinstance(value, str):
            # Handle comma-separated values
            tags = SheetImport.parse_array_field(value)
            # Clean and filter empty tags
            tags = [tag.strip() for tag in tags if tag.strip()]
            if tags:
                self.actor.tags = tags
                self.data_import.add_to_log(f"Processed tags")
        else:
            self.handle_mismatch("tags", value)

    def set_actor_type(self, field: str, map_item: Union[str, tuple]) -> None:
        """
        Sets the actor type based on the given map_item.

        Args:
            - field: The field to set the actor type for: "type" for fixed actor type, "dtype" for dynamic actor type.
            - map_item: The map item to determine the actor type.

        Returns:
            None

        Raises:
            None
        """
        restrict, trans = self.generate_translations("type")
        result = None
        value = None

        # fixed actor type
        if field == "type":
            # to ensure that the value has been set
            # in case of a mismatch
            result = value = map_item
        # dynamic actor type
        elif field == "dtype" and map_item[0].__class__ == str:
            value = self.row.get(map_item[0])
            result = SheetImport.closest_match(value, trans)

        if result:
            self.actor.type = restrict[trans.index(result)]
        else:
            self.handle_mismatch("type", value)

    def set_description(self, map_item: Any) -> None:
        """
        Method to set description.

        Args:
            - map_item: The map item to set the description.

        Returns:
            None
        """
        # return a string based on all different joined fields
        description = ""
        old_description = ""

        # save existing description
        # from any field/value mismatch
        if self.actor_profile.description:
            old_description = self.actor_profile.description
            self.actor_profile.description = ""

        for item in map_item:
            # first separator is always null
            sep = item.get("sep") or ""
            data = item.get("data")
            content = ""
            if data:
                content = self.row.get(data[0])

            description += "{} {}".format(sep, content)
            # separate joins by a new line
            description += "\n"

        if description:
            self.actor_profile.description = description
            if old_description:
                self.actor_profile.description += old_description
        self.data_import.add_to_log(f"Processed description")

    def set_events(self, map_item: Any) -> None:
        """
        Method to set events.

        Args:
            - map_item: The map item to set the events.

        Returns:
            None
        """
        events = []
        for event in map_item:
            e = {}
            for attr in event:
                # detect event type mode
                if attr == "type" and event.get(attr):
                    e["type"] = event.get(attr)
                else:
                    if event.get(attr):
                        e[attr] = self.row.get(event.get(attr)[0])
            # validate later
            events.append(e)

        if events:
            for event in events:
                if not event:
                    continue
                e = Event()
                title = event.get("title")
                if title:
                    e.title = str(title)

                e.comments = event.get("comments")
                # search and match event type
                type = event.get("type")
                if type:
                    eventtype = Eventtype.find_by_title(type)
                    if eventtype:
                        e.eventtype = eventtype

                location = event.get("location")
                loc = None
                if location:
                    loc = Location.find_by_title(location)
                    if loc:
                        e.location = loc
                from_date = event.get("from_date")
                if from_date:
                    e.from_date = DateHelper.parse_date(from_date)
                to_date = event.get("to_date")
                if to_date:
                    e.to_date = DateHelper.parse_date(to_date)

                # validate event here
                if (from_date and not pd.isnull(from_date)) or loc or title:
                    self.actor.events.append(e)
                else:
                    self.data_import.add_to_log(
                        f"Invalid event. Skipped due to missing or invalid from_date or missing location"
                    )
                    self.data_import.add_to_log(f"Event: {event}")
                    self.handle_mismatch("event", event)

    def set_reporters(self, map_item: Any) -> None:
        """
        Method to set location columns.

        Args:
            - map_item: The map item to set the reporters.

        Returns:
            None
        """
        reporters = []
        for reporter in map_item:
            r = {}
            for attr in reporter:
                r[attr] = self.row.get(reporter.get(attr)[0])
            reporters.append(r)
        if reporters:
            self.actor.reporters = reporters

    def handle_mismatch(self, field: str, value: Any) -> None:
        """
        Method to handle mismatched columns and
        data by logging the mismatch and appending
        data to the end of the Actor's description.

        Args:
            - field: The field that has a mismatch.
            - value: The value that caused the mismatch.

        Returns:
            None
        """
        self.data_import.add_to_log(f"Field value mismatch {field}.\n Appending to description.")
        self.actor_profile.description += f"</p>\n<p>{field}: {str(value)}"

    def gen_value(self, field: str) -> None:
        """
        Generate the value of a field mapping for a single row.

        This method retrieves the value from a CSV row based on the provided mapping.
        It handles various field mappings and sets the corresponding values accordingly.

        Args:
            field (str): The field to generate the value for.

        Returns:
            None
        """
        map_item = self.map.get(field)
        # more generic solution // get field value for simple mapped columns
        value = None
        if map_item[0].__class__ == str:
            value = self.row.get(map_item[0])

        self.data_import.add_to_log(f"Processing field: {field}, map_item: {map_item}")

        # handle complex list of dicts for reporters
        # detect reporters map
        if field == "tags":
            self.set_tags(value)
            return

        if field == "type" or field == "dtype":
            self.set_actor_type(field, map_item)
            return

        if field == "description":
            self.set_description(map_item)
            return

        elif field == "events":
            self.set_events(map_item)
            return

        elif field == "reporters":
            self.set_reporters(map_item)
            return

        elif field in config_dict.keys():
            self.set_from_list(field, value)
            return

        elif field in opts_list:
            self.set_opts(field, value)
            return

        elif field in details_list:
            self.set_details(field, value)
            return

        # basic form : directly mapped value
        elif len(map_item) == 1:
            if not value:
                # exit if csv value is empty
                return

            if field in location_list:
                return self.set_location(field, value)

            elif field in sec_dict.keys():
                self.set_secondaries(field, value)
                return

            elif field in date_list:
                self.set_date(field, value)
                return

            elif field in bool_list:
                self.set_bool(field, value)
                return

            # adding little improvement to strip extra white space in case it exists
            if value.__class__ == str:
                value = value.strip()

            # default case scenario set value directly to actor
            # check if the the value matches the column
            field_type = (
                getattr(ActorProfile, field).type.python_type
                if field in ActorProfile.__table__.columns
                else getattr(Actor, field).type.python_type
            )

            # cast the value into the correct type
            # this avoids errors caused by type mismatch
            value = field_type(value)

            try:
                self.set_actor_or_profile_attr(field, value)
            except:
                self.handle_mismatch(field, value)

    def import_row(self) -> None:
        """Function to import a single row from a CSV or XLSX file into the database."""
        time.sleep(0.01)

        self.data_import.processing()

        for field in self.map:
            # loop only selected mapped columns
            if len(self.map.get(field)) > 0:
                try:
                    self.gen_value(field)
                except Exception as e:
                    self.data_import.add_to_log("Failed to create Actor from row.")
                    self.data_import.add_to_log(f"Error processing {field}.")
                    self.data_import.fail(e)
                    return

        # check for unique entries
        if self.vmap:
            for field in list(self.vmap.keys()):
                # check if csv row actually has a value for this
                csv_value = getattr(self.actor, field)
                if csv_value:
                    if Actor.query.filter(getattr(Actor, field) == str(csv_value)).first():
                        self.data_import.fail(
                            f"Existing Actor with the same {field} detected. Skiping..."
                        )
                        return

        self.actor.comments = f"Created via Sheet Import - Batch: {self.batch_id}"
        self.actor.status = "Machine Created"

        # access roles
        if self.roles:
            self.actor.roles = []
            actor_roles = Role.query.filter(Role.id.in_([r.get("id") for r in self.roles])).all()
            self.actor.roles.extend(actor_roles)

        # check if profile should be MP
        for col in [col.name for col in ActorProfile.__table__.columns if col.comment == "MP"]:
            if getattr(self.actor_profile, col):
                self.actor_profile.mode = 3
                self.data_import.add_to_log(f"Changed Actor Profile to MP.")
                break

        # Save actor
        try:
            self.actor_profile.save(raise_exception=True)
            self.actor.meta = self.row.to_json(orient="index")
            self.actor.create_revision()

            # Creating Activity
            user = User.query.get(self.data_import.user_id)
            Activity.create(
                user, Activity.ACTION_CREATE, Activity.STATUS_SUCCESS, self.actor.to_mini(), "actor"
            )

            self.data_import.add_to_log(f"Created Actor {self.actor.id} successfully.")
            self.data_import.add_item(self.actor.id)
            self.data_import.sucess()

        except DatabaseException as e:
            self.data_import.add_to_log(f"Failed to create Actor from row.")
            self.data_import.fail(e)
