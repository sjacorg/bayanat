import re

import pandas as pd
from enferno.admin.models import Actor, Log, Event, Eventtype, Location, Label, Source
from enferno.utils.date_helper import DateHelper


class SheetUtils:

    def __init__(self, file_path, config=None):
        self.sheet = file_path
        self.config = config

    @staticmethod
    def parse_array_field(val):
        """
        static method to handle parsing of array csv columns
        :param val:column to parse
        :return: list of values
        """
        if not ',' in val:
            return [val.strip('"“” ')]
        rex = r'\"[^\"]+\"+|[^ , ]+'
        matches = re.findall(rex, val)
        matches = [match.strip('"“” ') for match in matches]
        return matches

    @staticmethod
    def closest_match(str, lst):
        """
        :param str: string to search for
        :param lst: list of values to pick from
        :return: matching list item in correct exact case
        """
        for item in lst:
            if item.lower().strip() == str.lower().strip():
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

    def gen_value(self, actor, row, field, map_item):
        """
        get value from a csv row based on the mapping provided
        this method generates the value of a field mapping for a single row
        :param field name of the field:
        :param row: a csv row
        :param map_item: mapping value
        :return: value based on row data and mapping provided
        """
        # handle complex list of dicts for reporters
        # detect reporters map

        print('Processing  ... {} '.format(field))

        if field == 'reporters':
            # return a list of values based on map list
            reporters = []
            for reporter in map_item:
                r = {}
                for attr in reporter:
                    r[attr] = row.get(reporter.get(attr)[0])
                reporters.append(r)
            if reporters:
                actor.reporters = reporters
            return actor

        if field == 'events':
            # return a list of values based on map list
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
                #validate later
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



                    #validate event here
                    if (from_date and not pd.isnull(from_date)) or loc:

                        actor.events.append(e)
            return actor

        if field == 'description':
            # return a string based on all different joined fields
            description = ''
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
            
            return actor

        # Detect and match fields for predefined actor lists
        if field == 'age':
            csv_val = row.get(map_item[0])
            restrict = self.config.get('actorAge')
            restrict = [x['en'] for x in restrict]
            if csv_val and restrict:
                age = SheetUtils.closest_match(csv_val, restrict)
                if age:
                    actor.age = age
                else:
                    print('Field value mismatch :: {}'.format(field))
            return actor

        if field == 'sex':
            csv_val = row.get(map_item[0])
            restrict = self.config.get('actorSex')
            restrict = [x['en'] for x in restrict]
            if csv_val and restrict:
                sex = SheetUtils.closest_match(csv_val, restrict)
                if sex:
                    actor.sex = sex
                else:
                    print('Field value mismatch :: {}'.format(field))
            return actor

        if field == 'civilian':
            csv_val = row.get(map_item[0])
            restrict = self.config.get('actorCivilian')
            restrict = [x['en'] for x in restrict]
            if csv_val and restrict:
                civilian = SheetUtils.closest_match(csv_val, restrict)
                if civilian:
                    actor.civilian = civilian
                else:
                    print('Field value mismatch :: {}'.format(field))
            return actor

        if field == 'actor_type':
            csv_val = row.get(map_item[0])
            restrict = self.config.get('actorTypes')
            restrict = [x['en'] for x in restrict]
            if csv_val and restrict:
                actor_type = SheetUtils.closest_match(csv_val, restrict)
                if actor_type:
                    actor.actor_type = actor_type
                else:
                    print('Field value mismatch :: {}'.format(field))
            return actor

        if field == 'ethnography':
            csv_val = row.get(map_item[0])
            #convert it to array
            ethnography = SheetUtils.parse_array_field(csv_val)
            restrict = self.config.get('actorEthno')
            restrict = [x['en'] for x in restrict]
            if ethnography:
                ethnography = [SheetUtils.closest_match(item, restrict) for item in ethnography if SheetUtils.closest_match(item, restrict)]
            if ethnography:
                actor.ethnography = ethnography
            else:
                print('Field value mismatch :: {}'.format(field))
            return actor

        if field == 'nationality':
            csv_val = row.get(map_item[0])
            nationality = SheetUtils.parse_array_field(csv_val)
            restrict = self.config.get('countries')
            restrict = [x['en'] for x in restrict]
            if nationality and restrict:
                nationality = [SheetUtils.closest_match(item, restrict) for item in nationality]
                nationality = [x for x in nationality if x]
            if nationality:
                actor.nationality = nationality
            else:
                print('Field value mismatch :: {}'.format(field))
            return actor

        if field == 'physique':
            csv_val = row.get(map_item[0])
            restrict = self.config.get('physique')
            restrict = [x['en'] for x in restrict]
            if csv_val and restrict:
                physique = SheetUtils.closest_match(csv_val, restrict)
                if physique:
                    actor.physique = physique
                else:
                    print('Field value mismatch :: {}'.format(field))
            return actor

        if field == 'hair_loss':
            csv_val = row.get(map_item[0])
            restrict = self.config.get('hairLoss')
            restrict = [x['en'] for x in restrict]
            if csv_val and restrict:
                hair_loss = SheetUtils.closest_match(csv_val, restrict)
                if hair_loss:
                    actor.hair_loss = hair_loss
                else:
                    print('Field value mismatch :: {}'.format(field))
            return actor

        if field == 'hair_type':
            csv_val = row.get(map_item[0])
            restrict = self.config.get('hairType')
            restrict = [x['en'] for x in restrict]
            if csv_val and restrict:
                hair_type = SheetUtils.closest_match(csv_val, restrict)
                if hair_type:
                    actor.hair_type = hair_type
                else:
                    print('Field value mismatch :: {}'.format(field))
            return actor

        if field == 'hair_length':
            csv_val = row.get(map_item[0])
            restrict = self.config.get('hairLength')
            restrict = [x['en'] for x in restrict]
            if csv_val and restrict:
                hair_length = SheetUtils.closest_match(csv_val, restrict)
                if hair_length:
                    actor.hair_length = hair_length
                else:
                    print('Field value mismatch :: {}'.format(field))
            return actor

        if field == 'hair_color':
            csv_val = row.get(map_item[0])
            restrict = self.config.get('hairColor')
            restrict = [x['en'] for x in restrict]
            if csv_val and restrict:
                hair_color = SheetUtils.closest_match(csv_val, restrict)
                if hair_color:
                    actor.hair_color = hair_color
                else:
                    print('Field value mismatch :: {}'.format(field))
            return actor

        if field == 'facial_hair':
            csv_val = row.get(map_item[0])
            restrict = self.config.get('facialHair')
            restrict = [x['en'] for x in restrict]
            if csv_val and restrict:
                facial_hair = SheetUtils.closest_match(csv_val, restrict)
                if facial_hair:
                    actor.facial_hair = facial_hair
            return actor

        if field == 'handedness':
            csv_val = row.get(map_item[0])
            restrict = self.config.get('handness')
            restrict = [x['en'] for x in restrict]
            if csv_val and restrict:
                handedness = SheetUtils.closest_match(csv_val, restrict)
                if handedness:
                    actor.handedness = handedness
                else:
                    print('Field value mismatch :: {}'.format(field))
            return actor

        if field == 'eye_color':
            csv_val = row.get(map_item[0])
            restrict = self.config.get('eyeColor')
            restrict = [x['en'] for x in restrict]
            if csv_val and restrict:
                eye_color = SheetUtils.closest_match(csv_val, restrict)
                if eye_color:
                    actor.eye_color = eye_color
                else:
                    print('Field value mismatch :: {}'.format(field))
            return actor


        if field == 'case_status':
            csv_val = row.get(map_item[0])
            restrict = self.config.get('caseStatus')
            restrict = [x['en'] for x in restrict]
            if csv_val and restrict:
                case_status = SheetUtils.closest_match(csv_val, restrict)
                if case_status:
                    actor.case_status = case_status
            return actor


        if field == 'smoker':
            csv_val = row.get(map_item[0])
            restrict = self.config.get('smoker')
            restrict = [x['en'] for x in restrict]
            if csv_val and restrict:
                smoker = SheetUtils.closest_match(csv_val, restrict)
                if smoker:
                    actor.smoker = smoker
                else:
                    print('Field value mismatch :: {}'.format(field))
            return actor


        # basic form : directly mapped value
        if len(map_item) == 1:
            value = row.get(map_item[0])
            if not value:
                # exit if csv value is empty
                return actor

            if field == 'labels':
                labels = SheetUtils.parse_array_field(value)
                for label in labels:
                    l = Label.find_by_title(label)
                    if l and not l in actor.labels:
                        actor.labels.append(l)
                return actor

            if field == 'verLabels':
                labels = SheetUtils.parse_array_field(value)

                for label in labels:
                    l = Label.find_by_title(label)
                    if l and not l in actor.ver_labels:
                        actor.ver_labels.append(l)
                return actor

            if field == 'sources':
                sources = SheetUtils.parse_array_field(value)
                for source in sources:
                    s = Source.find_by_title(source)
                    if s and not s in actor.sources:
                        actor.sources.append(s)
                return actor

            # location foreign keys
            if field == 'birth_place':
                location = Location.find_by_title(value)
                if location:
                    actor.birth_place = location
                return actor

            if field == 'residence_place':
                location = Location.find_by_title(value)
                if location:
                    actor.residence_place = location
                return actor
            if field == 'origin_place':
                location = Location.find_by_title(value)
                if location:
                    actor.origin_place = location
                return actor

            if field in ['birth_date', 'documentation_date', 'publish_date']:
                setattr(actor, field, DateHelper.parse_date(value))
                return actor

            # MP /MISC

            if field in ['dental_record', 'family_notified', 'missing_relatives', 'source_link_type']:

                if value.__class__ == str and value.lower() in ['y', 'yes', 'true', 't'] or value == 1:
                    setattr(actor, field, True)
                else:
                    setattr(actor, field, False)
                return actor


            if field == 'pregnant_at_disappearance':
                restrict = self.config.get('pregnant')
                restrict = [x['en'].lower() for x in restrict]
                if value.lower().strip() in restrict:
                    actor.pregnant_at_disappearance = value.strip().title()
                else:
                    print('Field value mismatch :: {}'.format(field))

                return actor

            if field == 'glasses':
                restrict = self.config.get('glasses')
                restrict = [x['en'].lower() for x in restrict]
                if value.lower().strip() in restrict:
                    actor.glasses = value.strip().title()
                else:
                    print('Field value mismatch :: {}'.format(field))

                return actor

            if field == 'seen_in_detention_opts' and value.lower().strip() in ['yes', 'no', 'unknown']:
                actor.seen_in_detention = actor.seen_in_detention or {}
                actor.seen_in_detention['opts'] = value.strip().capitalize()
                return actor

            if field == 'seen_in_detention_details':
                actor.seen_in_detention = actor.seen_in_detention or {}
                actor.seen_in_detention['details'] = value
                return actor

            if field == 'known_dead_opts' and value.lower().strip() in ['yes', 'no', 'unknown']:
                actor.known_dead = actor.known_dead or {}
                actor.known_dead['opts'] = value.strip().capitalize()
                return actor

            if field == 'known_dead_details':
                actor.known_dead = actor.known_dead or {}
                actor.known_dead['details'] = value
                return actor

            if field == 'injured_opts' and value.lower().strip() in ['yes', 'no', 'unknown']:
                actor.injured = actor.injured or {}
                actor.injured['opts'] = value.strip().capitalize()
                return actor

            if field == 'injured_details':
                actor.injured = actor.injured or {}
                actor.injured['details'] = value
                return actor

            if field == 'skin_markings_opts':
                actor.skin_markings = actor.skin_markings or {}
                skin_markings = SheetUtils.parse_array_field(value)
                restrict = self.config.get('skinMarkings')
                restrict = [x['en'] for x in restrict]
                if skin_markings and restrict:
                    skin_markings = [SheetUtils.closest_match(item, restrict) for item in skin_markings]
                    skin_markings = [x for x in skin_markings if x]
                if skin_markings:
                    actor.skin_markings['opts'] = skin_markings
                return actor

            if field == 'skin_markings_details':
                actor.skin_markings = actor.skin_markings or {}
                actor.skin_markings['details'] = value
                return actor

            # adding little improvement to strip extra white space in case it exists
            if value.__class__ == str:
                value = value.strip()
            # default case scenario set value directly to actor
            setattr(actor, field, value)
            return actor

    def import_sheet(self, map, target, batch_id, vmap=None, sheet=None):
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
                row_id = 'row-{}'.format(i)
                # print('processing row {}'.format(row))
                for item in map:
                    # loop only selected mapped columns

                    if len(map.get(item)) > 0:
                        actor = self.gen_value(actor, row, item, map.get(item))

                if vmap:
                    skip = False
                    for field in list(vmap.keys()):
                        # check if csv row actually has a value for this
                        csv_value = getattr(actor, field)
                        if csv_value and not skip:
                            if Actor.query.filter(getattr(Actor, field) == str(csv_value)).first():
                                print('Existing Actor with the same {} : {} detected, ignoring ..'.format(field,
                                                                                                          csv_value))
                                skip = True
                                continue
                    if skip:
                        Log.create(row_id, 'actor', 'import', batch_id, 'failed')
                        continue
                # print(actor.validate())
                # print(actor.__dict__)
                actor.comments = 'Created via CSV Import - Batch: {}'.format(batch_id)
                actor.status = 'Machine Created'
                if actor.save():
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
