from datetime import timedelta

from dateutil.parser import parse
from sqlalchemy import or_, not_, func, and_

from enferno.admin.models import Bulletin, Actor, Incident, Label, Source, Location, Event



class SearchUtils:

    ACCEPTED_DATE_RANGES = ['1d', '2d', '3d', '4d', '5d', '6d', '7d', '30d', '90d', '180d', '365d']

    def __init__(self, json=None, cls=None):
        self.search = json.get('q') if json else [{}]
        self.cls = cls

    def get_query(self):
        if self.cls == 'Bulletin':

            return self.build_bulletin_query()
        elif self.cls == 'Actor':
            return self.build_actor_query()
        elif self.cls == 'Incident':
            return self.build_incident_query()
        return []

    def to_dict(self):
        return self.args

    def build_bulletin_query(self):
        main = self.bulletin_query(self.search[0])
        if len(self.search) == 1:
            return [main], []
        # link queries starting from second item
        ops = []
        queries = [main]

        for i in range(1, len(self.search)):
            q = self.bulletin_query(self.search[i])
            op = self.search[i].get('op', 'or')
            if op == 'and':
                ops.append('intersect')
            elif op == 'or':
                ops.append('union')
            queries.append(q)
        return queries, ops

    def build_actor_query(self):
        main = self.actor_query(self.search[0])
        if len(self.search) == 1:
            return [main], []

        # link queries starting from second item
        ops = []
        queries = [main]

        for i in range(1, len(self.search)):
            q = self.actor_query(self.search[i])
            op = self.search[i].get('op', 'or')
            if op == 'and':
                ops.append('intersect')
            elif op == 'or':
                ops.append('union')
            queries.append(q)
        return queries, ops

    def build_incident_query(self):
        return self.incident_query(self.search)

    def bulletin_query(self, q):
        query = []

        tsv = q.get('tsv')
        if tsv:
            words = tsv.split(' ')
            qsearch = [Bulletin.search.ilike('%{}%'.format(word)) for word in words]
            query.extend(qsearch)

        # exclude  filter
        extsv = q.get('extsv')
        if extsv:
            words = extsv.split(' ')
            for word in words:
                query.append(not_(Bulletin.search.ilike('%{}%'.format(word))))

        # ref
        ref = q.get('ref')

        if ref:
            search = ['%' + r + '%' for r in ref]
            #get serach operator
            op = q.get('opref', False)
            if op:
                query.append(or_(func.array_to_string(Bulletin.ref, '').ilike(r) for r in search))
            else:
                query.append(and_(func.array_to_string(Bulletin.ref, '').ilike(r) for r in search))

        exref = q.get('exref')
        if exref:
            # get operator
            opexref = q.get('opexref')
            if opexref:
                subq = Bulletin.query.filter(and_(Bulletin.ref.any(x) for x in exref)).with_entities('id')
                query.append(~Bulletin.id.in_(subq))
            else:
                query.extend([~Bulletin.ref.any(ref) for ref in exref])

        labels = q.get('labels', [])
        if len(labels):
            ids = [item.get('id') for item in labels]
            if q.get('oplabels'):
                query.append(Bulletin.labels.any(Label.id.in_(ids)))
            else:
                query.extend([Bulletin.labels.any(Label.id == id) for id in ids])

        # Excluded labels
        exlabels = q.get('exlabels', [])
        if len(exlabels):
            ids = [item.get('id') for item in exlabels]
            query.append(~Bulletin.labels.any(Label.id.in_(ids)))

        vlabels = q.get('vlabels', [])
        if len(vlabels):
            ids = [item.get('id') for item in vlabels]
            if q.get('opvlabels'):
                # And query
                query.append(Bulletin.ver_labels.any(Label.id.in_(ids)))
            else:
                query.extend([Bulletin.ver_labels.any(Label.id == id) for id in ids])

        # Excluded vlabels
        exvlabels = q.get('exvlabels', [])
        if len(exvlabels):
            ids = [item.get('id') for item in exvlabels]
            query.append(~Bulletin.ver_labels.any(Label.id.in_(ids)))

        sources = q.get('sources', [])
        if len(sources):
            ids = [item.get('id') for item in sources]
            if q.get('opsources'):
                query.append(Bulletin.sources.any(Source.id.in_(ids)))
            else:
                query.extend([Bulletin.sources.any(Source.id == id) for id in ids])

        # Excluded sources
        exsources = q.get('exsources', [])
        if len(exsources):
            ids = [item.get('id') for item in exsources]
            query.append(~Bulletin.sources.any(Source.id.in_(ids)))

        locations = q.get('locations', [])
        if len(locations):
            ids = [item.get('id') for item in locations]
            all_ids = []
            for id in ids:
                all_ids += Location.query.get(id).find_children()
            if q.get('oplocations'):
                query.append(Bulletin.locations.any(Location.id.in_(all_ids)))
            else:
                for id in ids:
                    location = Location.query.get(id)
                    query.append(Bulletin.locations.any(Location.id.in_(location.find_children())))

                    
        # Excluded sources
        exlocations = q.get('exlocations', [])
        if len(exlocations):
            ids = [item.get('id') for item in exlocations]
            query.append(~Bulletin.locations.any(Location.id.in_(ids)))

        # event date
        edate = q.get('edate', None)
        edatewithin = q.get('edatewithin', '1d')
        if edate:
            if edatewithin in self.ACCEPTED_DATE_RANGES:
                diff = timedelta(days=int(edatewithin[:-1]))
                edate = parse(edate)
                query.append(Bulletin.events.any(Event.from_date.between(edate - diff, edate + diff)))

        elocation = q.get('elocation')
        if elocation:
            id = elocation.get('id', -1)
            query.append(Bulletin.events.any(Event.location_id.in_([id])))

        etype = q.get('etype', None)
        if etype:
            id = etype.get('id', -1)
            query.append(Bulletin.events.any(Event.eventtype_id == id))

        # publish date
        pubdate = q.get('pubdate', None)
        pubdatewithin = q.get('pubdatewithin', '1d')
        if pubdate:
            if pubdatewithin in self.ACCEPTED_DATE_RANGES:
                diff = timedelta(days=int(pubdatewithin[:-1]))
                pubdate = parse(pubdate)
                query.append(Bulletin.publish_date.between(pubdate - diff, pubdate + diff))

        # documentation date
        docdate = q.get('docdate', None)
        docdatewithin = q.get('docdatewithin', '1d')
        if docdate:
            if docdatewithin in self.ACCEPTED_DATE_RANGES:
                diff = timedelta(days=int(docdatewithin[:-1]))
                docdate = parse(docdate)
                query.append(Bulletin.documentation_date.between(docdate - diff, docdate + diff))

        # creation date
        created = q.get('created', None)
        created_within = q.get('createdwithin', '1d')
        if created:
            if created_within in self.ACCEPTED_DATE_RANGES:
                diff = timedelta(days=int(created_within[:-1]))
                created = parse(created)
                query.append(Bulletin.created_at.between(created - diff, created + diff))

        # modified date
        updated = q.get('updated', None)
        updated_within = q.get('updatedwithin', '1d')
        if updated:
            if updated_within in self.ACCEPTED_DATE_RANGES:
                diff = timedelta(days=int(updated_within[:-1]))
                updated = parse(updated)
                query.append(Bulletin.updated_at.between(updated - diff, updated + diff))
                

        # assigned user(s)
        assigned = q.get('assigned', [])
        if (assigned):
            query.append(Bulletin.assigned_to_id.in_(assigned))

        # unassigned
        unassigned = q.get('unassigned', None)
        if unassigned:
            query.append(Bulletin.assigned_to == None)

        # First peer reviewer
        fpr = q.get('reviewer', [])
        if fpr:
            query.append(Bulletin.first_peer_reviewer_id.in_(fpr))

        # workflow status
        status = q.get('status', None)
        if status:
            query.append(Bulletin.status == status)

        # review status
        review_action = q.get('reviewAction', None)
        if review_action:
            query.append(Bulletin.review_action == review_action)

        return query

    def actor_query(self, q):
        query = []

        tsv = q.get('tsv')
        if tsv:
            words = tsv.split(' ')
            qsearch = [Actor.search.ilike('%{}%'.format(word)) for word in words]
            query.extend(qsearch)

        # exclude  filter
        extsv = q.get('extsv')
        if extsv:
            words = extsv.split(' ')
            for word in words:
                query.append(not_(Actor.search.ilike('%{}%'.format(word))))


        labels = q.get('labels', [])
        if len(labels):
            ids = [item.get('id') for item in labels]
            if q.get('oplabels'):
                query.append(Actor.labels.any(Label.id.in_(ids)))
            else:
                query.extend([Actor.labels.any(Label.id == id) for id in ids])

        # Excluded labels
        exlabels = q.get('exlabels', [])
        if len(exlabels):
            ids = [item.get('id') for item in exlabels]
            query.append(~Actor.labels.any(Label.id.in_(ids)))

        vlabels = q.get('vlabels', [])
        if len(vlabels):
            ids = [item.get('id') for item in vlabels]
            if q.get('opvlabels'):
                # And query
                query.append(Actor.ver_labels.any(Label.id.in_(ids)))
            else:
                query.extend([Actor.ver_labels.any(Label.id == id) for id in ids])

        # Excluded vlabels
        exvlabels = q.get('exvlabels', [])
        if len(exvlabels):
            ids = [item.get('id') for item in exvlabels]
            query.append(~Actor.ver_labels.any(Label.id.in_(ids)))

        sources = q.get('sources', [])
        if len(sources):
            ids = [item.get('id') for item in sources]
            if q.get('opsources'):
                query.append(Actor.sources.any(Source.id.in_(ids)))
            else:
                query.extend([Actor.sources.any(Source.id == id) for id in ids])

        # Excluded sources
        exsources = q.get('exsources', [])
        if len(exsources):
            ids = [item.get('id') for item in exsources]
            query.append(~Actor.sources.any(Source.id.in_(ids)))

        # event date
        edate = q.get('edate', None)
        edatewithin = q.get('edatewithin', '1d')
        if edate:
            if edatewithin in self.ACCEPTED_DATE_RANGES:
                diff = timedelta(days=int(edatewithin[:-1]))
                edate = parse(edate)
                query.append(Actor.events.any(Event.from_date.between(edate - diff, edate + diff)))

        locations = q.get('locations', [])
        if len(locations):
            ids = [item.get('id') for item in locations]
            if q.get('oplocations'):
                query.append(Actor.locations.any(Location.id.in_(ids)))
            else:
                query.extend([Actor.locations.any(Location.id == id) for id in ids])

        # Excluded sources
        exlocations = q.get('exlocations', [])
        if len(exlocations):
            ids = [item.get('id') for item in exlocations]
            query.append(~Actor.locations.any(Location.id.in_(ids)))

        elocation = q.get('elocation')
        if elocation:
            id = elocation.get('id', -1)
            query.append(Actor.events.any(Event.location_id.in_([id])))

        etype = q.get('etype', None)
        if etype:
            id = etype.get('id', -1)
            query.append(Actor.events.any(Event.eventtype_id == id))

        # publish date
        pubdate = q.get('pubdate', None)
        pubdatewithin = q.get('pubdatewithin', '1d')
        if pubdate:
            if pubdatewithin in self.ACCEPTED_DATE_RANGES:
                diff = timedelta(days=int(pubdatewithin[:-1]))
                pubdate = parse(pubdate)
                query.append(Actor.publish_date.between(pubdate - diff, pubdate + diff))

        # documentation date
        docdate = q.get('docdate', None)
        docdatewithin = q.get('docdatewithin', '1d')
        if docdate:
            if docdatewithin in self.ACCEPTED_DATE_RANGES:
                diff = timedelta(days=int(docdatewithin[:-1]))
                docdate = parse(docdate)
                query.append(Actor.documentation_date.between(docdate - diff, docdate + diff))

        # assigned user(s)
        assigned = q.get('assigned', [])
        if (assigned):
            query.append(Actor.assigned_to_id.in_(assigned))

        # First peer reviewer
        fpr = q.get('reviewer', [])
        if fpr:
            query.append(Actor.first_peer_reviewer_id.in_(fpr))

        # workflow status
        status = q.get('status', None)
        if status:
            query.append(Actor.status == status)

        # review status
        review_action = q.get('reviewAction', None)
        if review_action:
            query.append(Actor.review_action == review_action)

        # ---------- Extra fields -------------

        # Occupation
        occupation = q.get('occupation', None)
        if occupation:
            search = '%{}%'.format(occupation)
            query.append(or_(Actor.occupation.ilike(search), Actor.occupation_ar.ilike(search)))

        # Position
        position = q.get('position', None)
        if position:
            search = '%{}%'.format(position)
            query.append(or_(Actor.position.ilike(search), Actor.position_ar.ilike(search)))

        # Spoken Dialects
        dialects = q.get('dialects', None)
        if dialects:
            search = '%{}%'.format(dialects)
            query.append(or_(Actor.dialects.ilike(search), Actor.dialects_ar.ilike(search)))

        # Family Status
        family_status = q.get('family_status', None)
        if family_status:
            search = '%{}%'.format(family_status)
            query.append(or_(Actor.family_status.ilike(search), Actor.family_status_ar.ilike(search)))

        # Sex
        sex = q.get('sex', None)
        if sex:
            query.append(Actor.sex == sex)

        # Age
        age = q.get('age', None)
        if age:
            query.append(Actor.age == age)

        # Civilian
        civilian = q.get('civilian', None)
        if civilian:
            query.append(Actor.civilian == civilian)

        # Actor type
        actor_type = q.get('actor_type', None)
        if actor_type:
            query.append(Actor.actor_type == actor_type)

        # Ethnography
        ethnography = q.get('ethnography', None)
        if ethnography:
            query.append(Actor.ethnography.any(ethnography))

        # Nationality
        nationality = q.get('nationality', None)
        if nationality:
            query.append(Actor.nationality.any(nationality))

        # Place of birth
        birth_place = q.get('birth_place', {})
        if birth_place:
            query.append(Actor.birth_place_id == birth_place.get('id'))

        # National ID card
        national_id_card = q.get('national_id_card', {})
        if national_id_card:
            search = '%{}%'.format(national_id_card)
            query.append(Actor.national_id_card.ilike(search))

        return query

    def incident_query(self, q):
        query = []

        tsv = q.get('tsv')
        if tsv:
            words = tsv.split(' ')
            qsearch = [Incident.search.ilike('%{}%'.format(word)) for word in words]
            query.extend(qsearch)

        # exclude  filter
        extsv = q.get('extsv')
        if extsv:
            words = extsv.split(' ')
            for word in words:
                query.append(not_(Incident.search.ilike('%{}%'.format(word))))


        labels = q.get('labels', [])
        if len(labels):
            ids = [item.get('id') for item in labels]
            if q.get('oplabels'):
                query.append(Incident.labels.any(Label.id.in_(ids)))
            else:
                query.extend([Incident.labels.any(Label.id == id) for id in ids])

        # Excluded labels
        exlabels = q.get('exlabels', [])
        if len(exlabels):
            ids = [item.get('id') for item in exlabels]
            query.append(~Incident.labels.any(Label.id.in_(ids)))

        vlabels = q.get('vlabels', [])
        if len(vlabels):
            ids = [item.get('id') for item in vlabels]
            if q.get('opvlabels'):
                # And query
                query.append(Incident.ver_labels.any(Label.id.in_(ids)))
            else:
                query.extend([Incident.ver_labels.any(Label.id == id) for id in ids])

        # Excluded vlabels
        exvlabels = q.get('exvlabels', [])
        if len(exvlabels):
            ids = [item.get('id') for item in exvlabels]
            query.append(~Incident.ver_labels.any(Label.id.in_(ids)))

        sources = q.get('sources', [])
        if len(sources):
            ids = [item.get('id') for item in sources]
            if q.get('opsources'):
                query.append(Incident.sources.any(Source.id.in_(ids)))
            else:
                query.extend([Incident.sources.any(Source.id == id) for id in ids])

        # Excluded sources
        exsources = q.get('exsources', [])
        if len(exsources):
            ids = [item.get('id') for item in exsources]
            query.append(~Incident.sources.any(Source.id.in_(ids)))

        locations = q.get('locations', [])
        if len(locations):
            ids = [item.get('id') for item in locations]
            if q.get('oplocations'):
                query.append(Incident.locations.any(Location.id.in_(ids)))
            else:
                query.extend([Incident.locations.any(Location.id == id) for id in ids])

        # Excluded sources
        exlocations = q.get('exlocations', [])
        if len(exlocations):
            ids = [item.get('id') for item in exlocations]
            query.append(~Incident.locations.any(Location.id.in_(ids)))

        elocation = q.get('elocation')
        if elocation:
            id = elocation.get('id', -1)
            query.append(Incident.events.any(Event.location_id.in_([id])))

        etype = q.get('etype', None)
        if etype:
            id = etype.get('id', -1)
            query.append(Incident.events.any(Event.eventtype_id == id))

        # publish date
        pubdate = q.get('pubdate', None)
        pubdatewithin = q.get('pubdatewithin', '1d')
        if pubdate:
            if pubdatewithin in self.ACCEPTED_DATE_RANGES:
                diff = timedelta(days=int(pubdatewithin[:-1]))
                pubdate = parse(pubdate)
                query.append(Incident.publish_date.between(pubdate - diff, pubdate + diff))

        # documentation date
        docdate = q.get('docdate', None)
        docdatewithin = q.get('docdatewithin', '1d')
        if docdate:
            if docdatewithin in self.ACCEPTED_DATE_RANGES:
                diff = timedelta(days=int(docdatewithin[:-1]))
                docdate = parse(docdate)
                query.append(Incident.documentation_date.between(docdate - diff, docdate + diff))

        # assigned user(s)
        assigned = q.get('assigned', [])
        if (assigned):
            query.append(Incident.assigned_to_id.in_(assigned))

        # First peer reviewer
        fpr = q.get('reviewer', [])
        if fpr:
            query.append(Incident.first_peer_reviewer_id.in_(fpr))

        # workflow status
        status = q.get('status', None)
        if status:
            query.append(Incident.status == status)

        # review status
        review_action = q.get('reviewAction', None)
        if review_action:
            query.append(Incident.review_action == review_action)

        return query
