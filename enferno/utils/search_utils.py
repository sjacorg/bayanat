from datetime import timedelta

from dateutil.parser import parse
from sqlalchemy import or_, not_, func, and_

from enferno.admin.models import Bulletin, Actor, Incident, Label, Source, Location, Event
from enferno.user.models import Role


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

        # Support query using a range of ids
        ids = q.get('ids')
        if ids:
            query.append(Bulletin.id.in_(ids))

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
            # children search ?
            recursive = q.get('childlabels', None)
            if q.get('oplabels'):
                # or operator
                if recursive:
                    # get ids of children // update ids 
                    result = Label.query.filter(Label.id.in_(ids)).all()
                    direct = [label for label in result]
                    all = direct + Label.get_children(direct)
                    #remove dups
                    all = list(set(all))
                    ids = [label.id for label in all]

                query.append(Bulletin.labels.any(Label.id.in_(ids)))
            else:
                # and operator (modify children search logic)
                if recursive:
                    direct = Label.query.filter(Label.id.in_(ids)).all()
                    for label in direct:
                        children = Label.get_children([label])
                        # add original label + uniquify list
                        children = list(set([label] + children))
                        ids = [child.id for child in children]
                        query.append(Bulletin.labels.any(Label.id.in_(ids)))

                else:
                    # non-recursive (apply and on all ids)
                    query.extend([Bulletin.labels.any(Label.id == id) for id in ids])

        # Excluded labels
        exlabels = q.get('exlabels', [])
        if len(exlabels):
            ids = [item.get('id') for item in exlabels]
            query.append(~Bulletin.labels.any(Label.id.in_(ids)))

        vlabels = q.get('vlabels', [])
        if len(vlabels):
            ids = [item.get('id') for item in vlabels]
            # children search ?
            recursive = q.get('childverlabels', None)
            if q.get('opvlabels'):
                # or operator
                if recursive:
                    # get ids of children // update ids
                    result = Label.query.filter(Label.id.in_(ids)).all()
                    direct = [label for label in result]
                    all = direct + Label.get_children(direct)
                    # remove dups
                    all = list(set(all))
                    ids = [label.id for label in all]

                query.append(Bulletin.ver_labels.any(Label.id.in_(ids)))
            else:
                # and operator (modify children search logic)
                if recursive:
                    direct = Label.query.filter(Label.id.in_(ids)).all()
                    for label in direct:
                        children = Label.get_children([label])
                        # add original label + uniquify list
                        children = list(set([label] + children))
                        ids = [child.id for child in children]
                        query.append(Bulletin.ver_labels.any(Label.id.in_(ids)))

                else:
                    # non-recursive (apply and on all ids)
                    query.extend([Bulletin.ver_labels.any(Label.id == id) for id in ids])

        # Excluded vlabels
        exvlabels = q.get('exvlabels', [])
        if len(exvlabels):
            ids = [item.get('id') for item in exvlabels]
            query.append(~Bulletin.ver_labels.any(Label.id.in_(ids)))

        sources = q.get('sources', [])
        if len(sources):
            ids = [item.get('id') for item in sources]
            # children search ?
            recursive = q.get('childsources', None)
            if q.get('opsources'):
                # or operator
                if recursive:
                    # get ids of children // update ids
                    result = Source.query.filter(Source.id.in_(ids)).all()
                    direct = [source for source in result]
                    all = direct + Source.get_children(direct)
                    # remove dups
                    all = list(set(all))
                    ids = [source.id for source in all]

                query.append(Bulletin.sources.any(Source.id.in_(ids)))
            else:
                # and operator (modify children search logic)
                if recursive:
                    direct = Source.query.filter(Source.id.in_(ids)).all()
                    for source in direct:
                        children = Source.get_children([source])
                        # add original label + uniquify list
                        children = list(set([source] + children))
                        ids = [child.id for child in children]
                        query.append(Bulletin.sources.any(Source.id.in_(ids)))

                else:
                    # non-recursive (apply and on all ids)
                    query.extend([Bulletin.sources.any(Source.id == id) for id in ids])

        # Excluded sources
        exsources = q.get('exsources', [])
        if len(exsources):
            ids = [item.get('id') for item in exsources]
            query.append(~Bulletin.sources.any(Source.id.in_(ids)))

        locations = q.get('locations', [])
        if locations:
            ids = [item.get('id') for item in locations]
            if q.get('oplocations'):
                # get all child locations
                locs = Location.query.with_entities(Location.id).filter(
                    or_(*[Location.id_tree.like('%[{}]%'.format(x)) for x in ids])).all()
                loc_ids = [loc.id for loc in locs]
                query.append(Bulletin.locations.any(Location.id.in_(loc_ids)))
            else:
                # get combined lists of ids for each location
                id_mix = [Location.get_children_by_id(id) for id in ids]
                query.extend(Bulletin.locations.any(Location.id.in_(i)) for i in id_mix)


                    
        # Excluded sources
        exlocations = q.get('exlocations', [])
        if len(exlocations):
            ids = [item.get('id') for item in exlocations]
            query.append(~Bulletin.locations.any(Location.id.in_(ids)))

        # event date
        edate = q.get('edate', None)
        edatewithin = q.get('edatewithin', None)
        if edate:
            if edatewithin in self.ACCEPTED_DATE_RANGES:
                diff = timedelta(days=int(edatewithin[:-1]))
                edate = parse(edate).date()
                query.append(Bulletin.events.any((func.date(Event.from_date) >= edate - diff) & (func.date(Event.from_date) <= edate + diff)))
            else:
                query.append(Bulletin.events.any(func.date(Event.from_date) == edate))

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
        pubdatewithin = q.get('pubdatewithin', None)
        if pubdate:
            if pubdatewithin in self.ACCEPTED_DATE_RANGES:
                diff = timedelta(days=int(pubdatewithin[:-1]))
                pubdate = parse(pubdate).date()
                query.append((func.date(Bulletin.publish_date) >= pubdate - diff) & (func.date(Bulletin.publish_date) <= pubdate + diff))
            else:
                query.append(func.date(Bulletin.publish_date) == pubdate)

        # documentation date
        docdate = q.get('docdate', None)
        docdatewithin = q.get('docdatewithin', None)
        if docdate:
            if docdatewithin in self.ACCEPTED_DATE_RANGES:
                diff = timedelta(days=int(docdatewithin[:-1]))
                docdate = parse(docdate).date()
                query.append((func.date(Bulletin.documentation_date) >= docdate - diff) & (func.date(Bulletin.documentation_date) <= docdate + diff))
            else:
                query.append(func.date(Bulletin.documentation_date) == docdate)

        # creation date
        created = q.get('created', None)
        created_within = q.get('createdwithin', None)
        if created:
            if created_within in self.ACCEPTED_DATE_RANGES:
                diff = timedelta(days=int(created_within[:-1]))
                created = parse(created).date()
                query.append((func.date(Bulletin.created_at) >= created - diff) & (func.date(Bulletin.created_at) <= created + diff))
            else:
                query.append(func.date(Bulletin.created_at) == created)

        # modified date
        updated = q.get('updated', None)
        updated_within = q.get('updatedwithin', None)
        if updated:
            if updated_within in self.ACCEPTED_DATE_RANGES:
                diff = timedelta(days=int(updated_within[:-1]))
                updated = parse(updated).date()
                query.append((func.date(Bulletin.updated_at) >= updated - diff) & (func.date(Bulletin.updated_at) <= updated + diff))
            else:
                query.append(func.date(Bulletin.updated_at) == updated)

        # Access Roles
        roles = q.get('roles')


        if roles:
            query.append(Bulletin.roles.any(Role.id.in_(roles)))
        if q.get('norole'):
            query.append(~Bulletin.roles.any())


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

        # Related to bulletin search
        rel_to_bulletin= q.get('rel_to_bulletin')
        if rel_to_bulletin:
            bulletin = Bulletin.query.get(int(rel_to_bulletin))
            if bulletin:
                ids = [b.get_other_id(bulletin.id) for b in bulletin.bulletin_relations]
                query.append(Bulletin.id.in_(ids))

        # Related to actor search
        rel_to_actor = q.get('rel_to_actor')
        if rel_to_actor:
            actor = Actor.query.get(int(rel_to_actor))
            if actor:
                ids = [b.bulletin_id for b in actor.bulletin_relations]
                query.append(Bulletin.id.in_(ids))

        # Related to incident search
        rel_to_incident = q.get('rel_to_incident')
        if rel_to_incident:
            incident = Incident.query.get(int(rel_to_incident))
            if incident:
                ids = [b.bulletin_id for b in incident.bulletin_relations]
                query.append(Bulletin.id.in_(ids))

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
        edatewithin = q.get('edatewithin', None)
        if edate:
            if edatewithin in self.ACCEPTED_DATE_RANGES:
                diff = timedelta(days=int(edatewithin[:-1]))
                edate = parse(edate).date()
                query.append(Actor.events.any((func.date(Event.from_date) >= edate - diff) & (func.date(Event.from_date) <= edate + diff)))
            else:
                query.append(Actor.events.any(func.date(Event.from_date) == edate))

        res_locations = q.get('resLocations', [])
        if res_locations:
            ids = [item.get('id') for item in res_locations]
            # get all child locations
            locs = Location.query.with_entities(Location.id).filter(
                or_(*[Location.id_tree.like('%[{}]%'.format(x)) for x in ids])).all()
            loc_ids = [loc.id for loc in locs]
            query.append(Actor.residence_place_id.in_(loc_ids))

        origin_locations = q.get('originLocations', [])
        if origin_locations:
            ids = [item.get('id') for item in origin_locations]
            # get all child locations
            locs = Location.query.with_entities(Location.id).filter(
                or_(*[Location.id_tree.like('%[{}]%'.format(x)) for x in ids])).all()
            loc_ids = [loc.id for loc in locs]
            query.append(Actor.origin_place_id.in_(loc_ids))


        # Excluded residence locations
        ex_res_locations = q.get('exResLocations', [])
        if ex_res_locations:
            ids = [item.get('id') for item in ex_res_locations]
            query.append(~Actor.residence_place.has(Location.id.in_(ids)))
            # Excluded residence locations

        ex_origin_locations = q.get('exOriginLocations', [])
        if ex_origin_locations:
            ids = [item.get('id') for item in ex_origin_locations]
            query.append(~Actor.origin_place.has(Location.id.in_(ids)))

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
        pubdatewithin = q.get('pubdatewithin', None)
        if pubdate:
            if pubdatewithin in self.ACCEPTED_DATE_RANGES:
                diff = timedelta(days=int(pubdatewithin[:-1]))
                pubdate = parse(pubdate)
                query.append(Actor.publish_date.between(pubdate - diff, pubdate + diff))
            else:
                query.append(Actor.publish_date == pubdate)

        # documentation date
        docdate = q.get('docdate', None)
        docdatewithin = q.get('docdatewithin', None)
        if docdate:
            if docdatewithin in self.ACCEPTED_DATE_RANGES:
                diff = timedelta(days=int(docdatewithin[:-1]))
                docdate = parse(docdate)
                query.append(Actor.documentation_date.between(docdate - diff, docdate + diff))
            else:
                query.append(Actor.documentation_date == docdate)

        # Access Roles
        roles = q.get('roles')

        if roles:
            query.append(Actor.roles.any(Role.id.in_(roles)))
        if q.get('norole'):
            query.append(~Actor.roles.any())

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

        # date of birth
        birth_date = q.get('birth_date')
        if birth_date:
            query.append(Actor.birth_date == birth_date)

        # National ID card
        national_id_card = q.get('national_id_card', {})
        if national_id_card:
            search = '%{}%'.format(national_id_card)
            query.append(Actor.national_id_card.ilike(search))

        # Related to bulletin search
        rel_to_bulletin= q.get('rel_to_bulletin')
        if rel_to_bulletin:
            bulletin = Bulletin.query.get(int(rel_to_bulletin))
            if bulletin:
                ids = [a.actor_id for a in bulletin.actor_relations]
                query.append(Actor.id.in_(ids))

        # Related to actor search
        rel_to_actor = q.get('rel_to_actor')
        if rel_to_actor:
            actor = Actor.query.get(int(rel_to_actor))
            if actor:
                ids = [a.get_other_id(actor.id) for a in actor.actor_relations]
                query.append(Actor.id.in_(ids))

        # Related to incident search
        rel_to_incident = q.get('rel_to_incident')
        if rel_to_incident:
            incident = Incident.query.get(int(rel_to_incident))
            if incident:
                ids = [a.actor_id for a in incident.actor_relations]
                query.append(Actor.id.in_(ids))


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
        if locations:
            ids = [item.get('id') for item in locations]
            if q.get('oplocations'):
                # get all child locations
                locs = Location.query.with_entities(Location.id).filter(
                    or_(*[Location.id_tree.like('%[{}]%'.format(x)) for x in ids])).all()
                loc_ids = [loc.id for loc in locs]
                query.append(Incident.locations.any(Location.id.in_(loc_ids)))
            else:
                # get combined lists of ids for each location
                id_mix = [Location.get_children_by_id(id) for id in ids]
                query.extend(Incident.locations.any(Location.id.in_(i)) for i in id_mix)


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

        # Access Roles
        roles = q.get('roles')

        if roles:
            query.append(Incident.roles.any(Role.id.in_(roles)))
        if q.get('norole'):
            query.append(~Incident.roles.any())

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


        # Related to bulletin search
        rel_to_bulletin= q.get('rel_to_bulletin')
        if rel_to_bulletin:
            bulletin = Bulletin.query.get(int(rel_to_bulletin))
            if bulletin:
                ids = [i.incident_id for i in bulletin.incident_relations]
                query.append(Incident.id.in_(ids))

        # Related to actor search
        rel_to_actor = q.get('rel_to_actor')
        if rel_to_actor:
            actor = Actor.query.get(int(rel_to_actor))
            if actor:
                ids = [i.incident_id for i in actor.incident_relations]
                query.append(Incident.id.in_(ids))

        # Related to incident search
        rel_to_incident = q.get('rel_to_incident')
        if rel_to_incident:
            incident = Incident.query.get(int(rel_to_incident))
            if incident:
                ids = [i.get_other_id(incident.id) for i in incident.incident_relations]
                query.append(Incident.id.in_(ids))

        return query
