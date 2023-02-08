import re

import pandas as pd
from enferno.admin.models import Actor, Log, Event, Eventtype, Location, Label, Source
from enferno.utils.date_helper import DateHelper
from enferno.user.models import Role
import gettext

# configurations

# add your own strings if needed
boolean_positive = ['y', 'yes', 'true', 't']
config_dict = {
    'age': 'actorAge',
    'sex': 'actorSex',
    'civilian':'actorCivilian',
    'actor_type': 'actorTypes',
    'ethnography': 'actorEthno',
    'nationality': 'countries',
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

class SheetUtils:

    def __init__(self, file_path, config=None, lang='en'):
        self.sheet = file_path
        self.config = config
        # set sheet language
        self.lang = lang
        # Install translator based on selected sheet language to be used for matching
        if lang != 'en':
            self.translator = gettext.translation('messages', localedir='enferno/translations', languages=[lang])
            self.translator.install()
        else:
            self.translator = None

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

    def parse_sheet(self):
        # read the file partially only for parsing purposes
        df = pd.read_csv(self.sheet, keep_default_na=False)
        df.dropna(how='all', axis=1, inplace=True)
        df = df.astype(str)

        columns = df.columns.to_list()
        head = df.head().to_dict()

        return {'columns': columns, 'head': head}

    def parse_xsheet(self, sheet):

        df = pd.read_excel(self.sheet, sheet_name=sheet)
        df.dropna(how='all', axis=1, inplace=True)
        df = df.astype(str)
        columns = df.columns.to_list()
        # drop nan values before generating head rows
        df.fillna('', inplace=True)
        head = df.head().to_dict()

        return {'columns': columns, 'head': head}

    def set_from_list(self, actor, field, value):
        """
        Method to set single and multi list columns.
        """
        # check if list allows one choice only
        one_choice = field not in ['ethnography', 'nationality']
        if value and not one_choice:
            value = SheetUtils.parse_array_field(value)
        # create a list from dict of entries in conf
        restrict = [x['en'] for x in self.config.get(config_dict[field])]
        # generate a list of transated strings if lang other than en
        # point to previous list if lang is eng
        trans = [self.translator.gettext(x) for x in restrict] if self.translator else restrict
        if value and restrict:
            if one_choice:
                result = SheetUtils.closest_match(value, trans)
            else:
                result = [SheetUtils.closest_match(item, trans) for item in value if
                          SheetUtils.closest_match(item, trans)]
            if result:
                if one_choice:
                    setattr(actor, field, restrict[trans.index(result)])
                # skin markings are kinda special
                elif field == 'skin_markings_opts':
                    actor.skin_markings['opts'] = [restrict[trans.index(x)] for x in result]
                else:
                    setattr(actor, field, [restrict[trans.index(x)] for x in result])
            else:
                return self.handle_mismatch(actor, field, value)
                
            print(f"Processed {field}")
        return actor

    def set_opts(self, actor, opts, value):
        """
        Method to set option columns.
        """
        field = opts.replace("_opts","")

        if not str(value).lower().strip() in ['yes', 'no', 'unknown']:
            return self.handle_mismatch(actor, field, value)

        attr = getattr(actor, field)
        if not attr:
            setattr(actor, field, {})
        getattr(actor, field)['opts'] = str(value).strip().capitalize()
        print(f"Processed {field}")
        return actor

    def set_details(self, actor, details, value):
        """
        Method to set details fields.
        """
        field = details.replace("_details","")
        attr = getattr(actor, field)
        if not attr:
            setattr(actor, field, {})
        getattr(actor, field)['details'] = str(value)
        print(f"Processed {field}")
        return actor

    def set_location(self, actor, field, value):
        """
        Method to set location columns.
        """
        location = Location.find_by_title(value)
        if location:
            setattr(actor, field, location)
            print(f"Processed {field}")
            return actor
        else:
            return self.handle_mismatch(actor, field, value)

    def set_secondaries(self, actor, field, value):
        """
        Method to set Labels and Sources.
        """
        items = SheetUtils.parse_array_field(value)
        for item in items:
            if field in ['labels', 'verLabels']:
                label = Label.find_by_title(item)
                if label and not label in actor.labels:
                    actor.labels.append(label)
            else:
                source = Source.find_by_title(item)
                if source and not source in actor.sources:
                    actor.sources.append(source)
        
        print(f"Processed {field}")
        return actor
    
    def set_date(self, actor, field, value):
        """
        Method to set date columns.
        """
        setattr(actor, field, DateHelper.parse_date(value))
        
        print(f"Processed {field}")
        return actor

    def set_bool(self, actor, field, value):
        """
        Method to set boolean columns.
        """
        if value.__class__ == str and value.lower() in boolean_positive or value == 1:
            setattr(actor, field, True)
        else:
            setattr(actor, field, False)
        print(f"Processed {field}")
        return actor
    
    def set_description(self, actor, row, map_item):
        """
        Method to set description.
        """
        # return a string based on all different joined fields
        description = ''
        old_description = ''

        # save existing description
        # from any field/value mismatch
        if actor.description:
            old_description = actor.description
            actor.description = ''

        for item in map_item:
            # first separator is always null
            sep = item.get('sep') or ''
            data = item.get('data')
            content = ''
            if data:
                content = row.get(data[0])

            description += '{} {}'.format(sep, content)
            # separate joins by a new line
            description += '\n'

        if description:
            actor.description = description
            if old_description:
                actor.description += old_description
        print(f"Processed description")
        return actor
    
    def set_events(self, actor, row, map_item):
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
                        e[attr] = row.get(event.get(attr)[0])
            # validate later
            events.append(e)

        if events:
            if actor.name == None:
                actor.name = 'temp'
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
                    actor.events.append(e)

        return actor
    
    def set_reporters(self, actor, row, map_item):
        """
        Method to set location columns.
        """
        reporters = []
        for reporter in map_item:
            r = {}
            for attr in reporter:
                r[attr] = row.get(reporter.get(attr)[0])
            reporters.append(r)
        if reporters:
            actor.reporters = reporters
        return actor

    def handle_mismatch(self, actor, field, value):
        """
        Method to handle mismatched columns and
        data by logging the mismatch and appending
        data to the end of the Actor's description.
        """
        print(f'Field value mismatch {field}.\n Appending to description.')
        actor.description += f'</p>\n<p>{field}: {value}'
        return actor

    def gen_value(self, actor, row, field, map_item):
        """
        get value from a csv row based on the mapping provided
        this method generates the value of a field mapping for a single row
        :param actor actor to assign value to
        :param field name of the field:
        :param row: a csv row
        :param map_item: mapping value
        :return: value based on row data and mapping provided
        """
        value = row.get(map_item[0])
        print(f'Processing field: {field}, map_item: {map_item}')
        
        # handle complex list of dicts for reporters
        # detect reporters map
        
        if field == 'description':
            return self.set_description(actor, row, map_item)

        elif field == 'events':
            return self.set_events(actor, row, map_item)

        elif field == 'reporters':
            return self.set_reporters(actor, row, map_item)
        
        elif field in config_dict.keys():
            return self.set_from_list(actor, field, value)

        elif field in opts_list:
            return self.set_opts(actor, field, value)

        elif field in details_list:
            return self.set_details(actor, field, value)

        # basic form : directly mapped value
        elif len(map_item) == 1:
            if not value:
                # exit if csv value is empty
                return actor

            if field in location_list:
                return self.set_location(actor, field, value)

            elif field in ['labels', 'verLabels', 'sources']:
                return self.set_secondaries(actor, field, value)

            elif field in date_list:
                return self.set_date(actor, field, value)
            
            elif field in bool_list:
                return self.set_bool(actor, field, value)

            # adding little improvement to strip extra white space in case it exists
            if value.__class__ == str:
                value = value.strip()

            # default case scenario set value directly to actor
            # check if the the value matches the column
            field_type = getattr(Actor, field).type.python_type
            if field_type == type(value) or field_type == 'str':
                setattr(actor, field, value)
                return actor
            elif field_type == 'int':
                try:
                    setattr(actor, field, int(value))
                except:
                    return self.handle_mismatch(actor, field, value)
            else:
                # if not append to description
                return self.handle_mismatch(actor, field, value)

    def import_sheet(self, map, target, batch_id, vmap=None, sheet=None, roles=[]):
        if target == 'actor':

            if sheet:
                df = pd.read_excel(self.sheet, sheet_name=sheet, keep_default_na=False)
            else:
                df = pd.read_csv(self.sheet, keep_default_na=False)
            df.drop_duplicates(inplace=True)

            df.fillna('')

            for i, row in df.iterrows():
                # for simulation purposes
                import time
                time.sleep(0.01)
                # ----------
                # Create a new actor for each csv row
                actor = Actor()
                actor.description = ''
                row_id = 'row-{}'.format(i)
                for item in map:
                    # loop only selected mapped columns

                    if len(map.get(item)) > 0:
                        try:
                            actor = self.gen_value(actor, row, item, map.get(item))
                        except Exception as e:
                            Log.create(row_id, 'actor', 'import', batch_id, 'failed')
                            print(f"Failed to create Actor from row {row_id}")
                            print(e)
                            break

                if vmap:
                    skip = False
                    for field in list(vmap.keys()):
                        # check if csv row actually has a value for this
                        csv_value = getattr(actor, field)
                        if csv_value and not skip:
                            if Actor.query.filter(getattr(Actor, field) == str(csv_value)).first():
                                print(f'Existing Actor with the same {field} detected. Skiping...')
                                skip = True
                                continue
                    if skip:
                        Log.create(row_id, 'actor', 'import', batch_id, 'failed')
                        continue

                actor.comments = 'Created via CSV Import - Batch: {}'.format(batch_id)
                actor.status = 'Machine Created'
                # access roles
                if roles:
                    actor.roles = []
                    actor_roles = Role.query.filter(Role.id.in_([r.get('id') for r in roles])).all()
                    actor.roles.extend(actor_roles)

                if actor.save():
                    actor.meta = row.to_json(orient='index')
                    actor.create_revision()
                    Log.create(row_id, 'actor', 'import', batch_id, 'success', meta=actor.to_mini())
                else:
                    Log.create(row_id, 'actor', 'import', batch_id, 'Failed', meta={'reason': 'Failed creating actor'})

        else:
            print('Wrong target provided')
            return False

    def get_sheets(self):
        xls = pd.ExcelFile(self.sheet)
        return xls.sheet_names
