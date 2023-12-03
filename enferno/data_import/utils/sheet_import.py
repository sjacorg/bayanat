import re
import time

import pandas as pd

from enferno.admin.models import Actor, Event, Eventtype, Location, Label, Source, Country, Ethnography, Activity
from enferno.data_import.models import DataImport

from enferno.utils.base import DatabaseException
from enferno.utils.date_helper import DateHelper
from enferno.user.models import Role, User
import gettext

# configurations

# add your own strings if needed
boolean_positive = ['y', 'yes', 'true', 't']
config_dict = {
    'age': 'actorAge',
    'sex': 'actorSex',
    'civilian':'actorCivilian',
    'actor_type': 'actorTypes',
    'physique': 'physique',
    'hair_loss': 'hairLoss',
    'hair_type': 'hairType',
    'hair_length': 'hairLength',
    'hair_color': 'hairColor',
    'facial_hair': 'facialHair',
    'handedness': 'handness',
    'eye_color': 'eyeColor',
    'case_status': 'caseStatus',
    'smoker': 'smoker',
    'pregnant_at_disappearance': 'pregnant',
    'glasses': 'glasses',
    'skin_markings_opts': 'skinMarkings'
}

sec_dict = {
    'labels': {'model': Label, 'attr': 'labels'}, 
    'verLabels': {'model': Label, 'attr': 'labels'},
    'sources': {'model': Source, 'attr': 'sources'},
    'ethnography': {'model': Ethnography, 'attr': 'ethnographies'},
    'nationality': {'model': Country, 'attr': 'nationalities'}
}

details_list =['seen_in_detention_details', 
                'known_dead_details', 
                'injured_details', 
                'skin_markings_details']

opts_list = ['seen_in_detention_opts', 
            'known_dead_opts', 
            'injured_opts']

bool_list = ['dental_record', 
            'family_notified', 
            'missing_relatives', 
            'source_link_type']

location_list = ['birth_place', 'origin_place', 'residence_place']
date_list = ['birth_date', 'documentation_date', 'publish_date']
  
  
class SheetImport:

    def __init__(self, filepath, sheet, row_id, data_import_id, map, batch_id, vmap=None, roles=[], config=None, lang='en',):
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
        self.actor.description = ''

        # Install translator based on selected sheet language to be used for matching
        if lang != 'en':
            self.translator = gettext.translation('messages', localedir='enferno/translations', languages=[lang])
            self.translator.install()
        else:
            self.translator = None

    @staticmethod
    def parse_csv(filepath):
        # read the file partially only for parsing purposes
        df = pd.read_csv(filepath, keep_default_na=False)
        df.dropna(how='all', axis=1, inplace=True)
        df = df.astype(str)

        columns = df.columns.to_list()
        head = df.head().to_dict()

        return {'columns': columns, 'head': head}

    @staticmethod
    def parse_excel(filepath, sheet):
        df = pd.read_excel(filepath, sheet_name=sheet)
        df.dropna(how='all', axis=1, inplace=True)
        df = df.astype(str)

        columns = df.columns.to_list()
        # drop nan values before generating head rows
        df.fillna('', inplace=True)
        head = df.head().to_dict()

        return {'columns': columns, 'head': head}

    @staticmethod
    def get_sheets(filepath):
        xls = pd.ExcelFile(filepath)
        return xls.sheet_names

    @staticmethod
    def sheet_to_df(filepath, sheet=None):
        """
        Parses CSV or XLSX file.
        :param filepath: path to sheets file
        :param sheet: sheet name for XLSX files (optional)
        """
        if sheet:
            df = pd.read_excel(filepath, sheet_name=sheet, keep_default_na=False)
        else:
            df = pd.read_csv(filepath, keep_default_na=False)

        df.drop_duplicates(inplace=True)
        df.fillna('')

        return df

    @staticmethod
    def parse_array_field(val):
        """
        static method to handle parsing of array csv columns
        :param val:column to parse
        :return: list of values
        """
        if ',' not in val:
            return [val.strip('"“” ')]
        rex = r'\"[^\"]+\"+|[^ , ]+'
        matches = re.findall(rex, val)
        matches = [match.strip('"“” ') for match in matches]
        return matches

    @staticmethod
    def closest_match(txt, lst):
        """
        :param txt: string to search for
        :param lst: list of values to pick from
        :return: matching list item in correct exact case
        """
        for item in lst:
            if item.lower().strip() == txt.lower().strip():
                return item
        return None

    def set_from_list(self, field, value):
        """
        Method to set single and multi list columns.
        """
        # check if list allows one choice only
        one_choice = field not in ['ethnography', 'nationality']
        if value and not one_choice:
            value = SheetImport.parse_array_field(value)
        # create a list from dict of entries in conf
        restrict = [x['en'] for x in self.config.get(config_dict[field])]
        # generate a list of translated strings if lang other than en
        # point to previous list if lang is eng
        trans = [self.translator.gettext(x) for x in restrict] if self.translator else restrict
        if value and restrict:
            if one_choice:
                result = SheetImport.closest_match(value, trans)
            else:
                result = [SheetImport.closest_match(item, trans) for item in value if
                          SheetImport.closest_match(item, trans)]
            if result:
                if one_choice:
                    setattr(self.actor, field, restrict[trans.index(result)])
                # skin markings are kinda special
                elif field == 'skin_markings_opts':
                    self.actor.skin_markings['opts'] = [restrict[trans.index(x)] for x in result]
                else:
                    setattr(self.actor, field, [restrict[trans.index(x)] for x in result])
            else:
                return self.handle_mismatch(field, value)
            
            self.data_import.add_to_log(f"Processed {field}")

    def set_opts(self, opts, value):
        """
        Method to set option columns.
        """
        field = opts.replace("_opts","")

        if not str(value).lower().strip() in ['yes', 'no', 'unknown']:
            return self.handle_mismatch(field, value)

        attr = getattr(self.actor, field)
        if not attr:
            setattr(self.actor, field, {})
        getattr(self.actor, field)['opts'] = str(value).strip().capitalize()
        self.data_import.add_to_log(f"Processed {field}")

    def set_details(self, details, value):
        """
        Method to set details fields.
        """
        field = details.replace("_details","")
        attr = getattr(self.actor, field)
        if not attr:
            setattr(self.actor, field, {})
        getattr(self.actor, field)['details'] = str(value)
        self.data_import.add_to_log(f"Processed {field}")

    def set_location(self, field, value):
        """
        Method to set location columns.
        """
        location = Location.find_by_title(value)
        if location:
            setattr(self.actor, field, location)
            self.data_import.add_to_log(f"Processed {field}")
        else:
            return self.handle_mismatch(field, value)

    def set_secondaries(self, field, value):
        """
        Method to set Labels and Sources.
        """
        model = sec_dict[field]['model']
        attr = sec_dict[field]['attr']

        items = SheetImport.parse_array_field(value)

        # set to avoid dups
        s = set()
        for item in items:
            x = model.find_by_title(item)
            if x:
                s.add(x)

        if s:
            setattr(self.actor, attr, list(s))
        self.data_import.add_to_log(f"Processed {field}")
    
    def set_date(self, field, value):
        """
        Method to set date columns.
        """
        setattr(self.actor, field, DateHelper.parse_date(value))
        
        self.data_import.add_to_log(f"Processed {field}")

    def set_bool(self, field, value):
        """
        Method to set boolean columns.
        """
        if value.__class__ == str and value.lower() in boolean_positive or value == 1:
            setattr(self.actor, field, True)
        else:
            setattr(self.actor, field, False)
        self.data_import.add_to_log(f"Processed {field}")
    
    def set_description(self, map_item):
        """
        Method to set description.
        """
        # return a string based on all different joined fields
        description = ''
        old_description = ''

        # save existing description
        # from any field/value mismatch
        if self.actor.description:
            old_description = self.actor.description
            self.actor.description = ''

        for item in map_item:
            # first separator is always null
            sep = item.get('sep') or ''
            data = item.get('data')
            content = ''
            if data:
                content = self.row.get(data[0])

            description += '{} {}'.format(sep, content)
            # separate joins by a new line
            description += '\n'

        if description:
            self.actor.description = description
            if old_description:
                self.actor.description += old_description
        self.data_import.add_to_log(f"Processed description")
    
    def set_events(self, map_item):
        """
        Method to set events.
        """
        events = []
        for event in map_item:
            e = {}
            for attr in event:
                # detect event type mode
                if attr == 'etype' and event.get(attr):
                    e['type'] = event.get(attr)
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
                title = event.get('title')
                if title:
                    e.title = str(title)

                e.comments = event.get('comments')
                # search and match event type
                type = event.get('type')
                if type:
                    eventtype = Eventtype.find_by_title(type)
                    if eventtype:
                        e.eventtype = eventtype

                location = event.get('location')
                loc = None
                if location:
                    loc = Location.find_by_title(location)
                    if loc:
                        e.location = loc
                from_date = event.get('from_date')
                if from_date:
                    e.from_date = DateHelper.parse_date(from_date)
                to_date = event.get('to_date')
                if to_date:
                    e.to_date = DateHelper.parse_date(to_date)

                # validate event here
                if (from_date and not pd.isnull(from_date)) or loc:
                    self.actor.events.append(e)
                else:
                    self.data_import.add_to_log(f'Invalid event. Skipped due to invalid from_date or missing location {e.__dict__}')
    
    def set_reporters(self, map_item):
        """
        Method to set location columns.
        """
        reporters = []
        for reporter in map_item:
            r = {}
            for attr in reporter:
                r[attr] = self.row.get(reporter.get(attr)[0])
            reporters.append(r)
        if reporters:
            self.actor.reporters = reporters

    def handle_mismatch(self, field, value):
        """
        Method to handle mismatched columns and
        data by logging the mismatch and appending
        data to the end of the Actor's description.
        """
        self.data_import.add_to_log(f'Field value mismatch {field}.\n Appending to description.')
        self.actor.description += f'</p>\n<p>{field}: {value}'

    def gen_value(self, field):
        """
        get value from a csv row based on the mapping provided
        this method generates the value of a field mapping for a single row
        :param actor actor to assign value to
        :param field name of the field:
        :param row: a csv row
        :param map_item: mapping value
        :return: value based on row data and mapping provided
        """
        map_item = self.map.get(field)
        # more generic solution // get field value for simple mapped columns
        if map_item[0].__class__ == str:
            value = self.row.get(map_item[0])

        self.data_import.add_to_log(f'Processing field: {field}, map_item: {map_item}')
        
        # handle complex list of dicts for reporters
        # detect reporters map
        
        if field == 'description':
            self.set_description(map_item)
            return

        elif field == 'events':
            self.set_events(map_item)
            return

        elif field == 'reporters':
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
            field_type = getattr(Actor, field).type.python_type
            if field_type == type(value) or field_type == 'str':
                setattr(self.actor, field, value)
            elif field_type == 'int':
                try:
                    setattr(self.actor, field, int(value))
                except:
                    self.handle_mismatch(field, value)
            else:
                # if not append to description
                self.handle_mismatch(field, value)

    def import_row(self):
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
                        self.data_import.fail(f'Existing Actor with the same {field} detected. Skiping...')
                        return

        self.actor.comments = F'Created via Sheet Import - Batch: {self.batch_id}'
        self.actor.status = 'Machine Created'

        # access roles
        if self.roles:
            self.actor.roles = []
            actor_roles = Role.query.filter(Role.id.in_([r.get('id') for r in self.roles])).all()
            self.actor.roles.extend(actor_roles)

        # Save actor
        try:
            self.actor.save(raise_exception=True)
            self.actor.meta = self.row.to_json(orient='index')
            self.actor.create_revision()

            # Creating Activity
            user = User.query.get(self.data_import.user_id)
            Activity.create(user, Activity.ACTION_CREATE, self.actor.to_mini(), 'actor')

            self.data_import.add_to_log(f"Created Actor {self.actor.id} successfully.")
            self.data_import.add_item(self.actor.id)
            self.data_import.sucess()

        except DatabaseException as e:
            self.data_import.add_to_log(f"Failed to create Actor from row.")
            self.data_import.fail(e)
