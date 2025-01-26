from dateutil.parser import parse
from sqlalchemy import or_, not_, and_, any_, all_, func, select, text
from sqlalchemy.sql.elements import BinaryExpression, ColumnElement

from enferno.admin.models import (
    Bulletin,
    Actor,
    Incident,
    Label,
    Source,
    Location,
    Event,
    LocationAdminLevel,
    PotentialViolation,
    ClaimedViolation,
    Ethnography,
    Country,
    Dialect,
    ActorProfile,
    Activity,
)
from enferno.user.models import Role


# helper methods


def date_between_query(field: ColumnElement, dates: list) -> BinaryExpression:
    """
    Create a date range query for a given field.

    Args:
        - field: The field to search on.
        - dates: A list of two dates in string format.

    Returns:
        - A binary expression for the date range query.
    """
    start_date = parse(dates[0]).date()
    if len(dates) == 1:
        end_date = start_date
    else:
        end_date = parse(dates[1]).date()
    return func.date(field).between(start_date, end_date)


class SearchUtils:
    """Utility class to build search queries for different models."""

    def __init__(self, json=None, cls=None):
        self.search = json.get("q") if json else [{}]
        self.cls = cls

    def get_query(self):
        """Get the query for the given class."""
        if self.cls == "bulletin":
            # Get conditions from first query
            main_stmt, conditions = self.bulletin_query(self.search[0])
            final_conditions = conditions

            # Handle nested queries by combining conditions
            if len(self.search) > 1:
                for i in range(1, len(self.search)):
                    _, next_conditions = self.bulletin_query(self.search[i])
                    op = self.search[i].get("op", "or")

                    if op == "and":
                        final_conditions.extend(next_conditions)
                    elif op == "or":
                        # Combine conditions with OR
                        final_conditions = [or_(*conditions, *next_conditions)]

            # Build final query with all conditions and default sorting
            result = select(Bulletin)
            if final_conditions:
                result = result.where(and_(*final_conditions))
            return result
        return []

    def to_dict(self):
        """Return the search arguments."""
        return self.args

    def bulletin_query(self, q: dict):
        """Build a select statement for bulletin search"""
        stmt = select(Bulletin)
        conditions = []

        # Support query using a range of ids
        if ids := q.get("ids"):
            conditions.append(Bulletin.id.in_(ids))

        # Text search
        if tsv := q.get("tsv"):
            words = tsv.split(" ")
            words = [f"%{w}%" for w in words]
            conditions.append(Bulletin.search.ilike(all_(words)))

        # Exclude text search
        if extsv := q.get("extsv"):
            words = extsv.split(" ")
            words = [f"%{w}%" for w in words]
            conditions.append(Bulletin.search.notilike(all_(words)))

        # Tags
        if ref := q.get("tags"):
            if q.get("inExact", False):
                # Must match any SINGLE tag exactly (equivalent to old version)
                conditions.append(or_(Bulletin.tags.contains([r]) for r in ref))
            else:
                # For partial matches, use ANY with ILIKE
                patterns = [f"%{r}%" for r in ref]
                conditions.append(Bulletin.tags_search.ilike(any_(patterns)))

            # Handle AND operation
            if q.get("opTags", False):
                if q.get("inExact", False):
                    # Must contain ALL individual tags
                    conditions[-1] = and_(Bulletin.tags.contains([r]) for r in ref)
                else:
                    patterns = [f"%{r}%" for r in ref]
                    conditions[-1] = Bulletin.tags_search.ilike(all_(patterns))

        # Exclude tags
        if exref := q.get("exTags"):
            if q.get("exExact", False):
                # Must NOT contain ANY of these tags individually
                conditions.append(and_(~Bulletin.tags.contains([r]) for r in exref))
            else:
                # Must NOT match ANY of these patterns - using raw SQL with trigram operator
                patterns = [f"%{r}%" for r in exref]
                patterns_sql = ",".join(f"'{p}'" for p in patterns)
                raw_sql = text(
                    f"NOT EXISTS (SELECT 1 FROM bulletin b2 WHERE b2.id = bulletin.id "
                    f"AND b2.tags_search ILIKE ANY(ARRAY[{patterns_sql}]))"
                )
                conditions.append(raw_sql)

            # Handle OR operation for exclusions
            if q.get("opExTags"):
                if q.get("exExact", False):
                    # Must NOT contain at least one tag (OR of NOTs)
                    conditions[-1] = or_(~Bulletin.tags.contains([r]) for r in exref)
                else:
                    patterns = [f"%{r}%" for r in exref]
                    patterns_sql = ",".join(f"'{p}'" for p in patterns)
                    raw_sql = text(
                        f"NOT EXISTS (SELECT 1 FROM bulletin b2 WHERE b2.id = bulletin.id "
                        f"AND b2.tags_search ILIKE ALL(ARRAY[{patterns_sql}]))"
                    )
                    conditions[-1] = raw_sql

        # Labels
        if labels := q.get("labels", []):
            ids = [item.get("id") for item in labels]
            recursive = q.get("childlabels", None)
            if q.get("oplabels"):
                if recursive:
                    result = db.session.query(Label).filter(Label.id.in_(ids)).all()
                    direct = [label for label in result]
                    all_labels = direct + Label.get_children(direct)
                    all_labels = list(set(all_labels))
                    ids = [label.id for label in all_labels]
                conditions.append(Bulletin.labels.any(Label.id.in_(ids)))
            else:
                if recursive:
                    direct = db.session.query(Label).filter(Label.id.in_(ids)).all()
                    for label in direct:
                        children = Label.get_children([label])
                        children = list(set([label] + children))
                        ids = [child.id for child in children]
                        conditions.append(Bulletin.labels.any(Label.id.in_(ids)))
                else:
                    conditions.extend([Bulletin.labels.any(Label.id == id) for id in ids])

        # Excluded labels
        if exlabels := q.get("exlabels", []):
            ids = [item.get("id") for item in exlabels]
            conditions.append(~Bulletin.labels.any(Label.id.in_(ids)))

        # Verification labels
        if vlabels := q.get("vlabels", []):
            ids = [item.get("id") for item in vlabels]
            recursive = q.get("childverlabels", None)
            if q.get("opvlabels"):
                if recursive:
                    result = db.session.query(Label).filter(Label.id.in_(ids)).all()
                    direct = [label for label in result]
                    all_labels = direct + Label.get_children(direct)
                    all_labels = list(set(all_labels))
                    ids = [label.id for label in all_labels]
                conditions.append(Bulletin.ver_labels.any(Label.id.in_(ids)))
            else:
                if recursive:
                    direct = db.session.query(Label).filter(Label.id.in_(ids)).all()
                    for label in direct:
                        children = Label.get_children([label])
                        children = list(set([label] + children))
                        ids = [child.id for child in children]
                        conditions.append(Bulletin.ver_labels.any(Label.id.in_(ids)))
                else:
                    conditions.extend([Bulletin.ver_labels.any(Label.id == id) for id in ids])

        # Excluded verification labels
        if exvlabels := q.get("exvlabels", []):
            ids = [item.get("id") for item in exvlabels]
            conditions.append(~Bulletin.ver_labels.any(Label.id.in_(ids)))

        # Sources
        if sources := q.get("sources", []):
            ids = [item.get("id") for item in sources]
            recursive = q.get("childsources", None)
            if q.get("opsources"):
                if recursive:
                    result = db.session.query(Source).filter(Source.id.in_(ids)).all()
                    direct = [source for source in result]
                    all_sources = direct + Source.get_children(direct)
                    all_sources = list(set(all_sources))
                    ids = [source.id for source in all_sources]
                conditions.append(Bulletin.sources.any(Source.id.in_(ids)))
            else:
                if recursive:
                    direct = db.session.query(Source).filter(Source.id.in_(ids)).all()
                    for source in direct:
                        children = Source.get_children([source])
                        children = list(set([source] + children))
                        ids = [child.id for child in children]
                        conditions.append(Bulletin.sources.any(Source.id.in_(ids)))
                else:
                    conditions.extend([Bulletin.sources.any(Source.id == id) for id in ids])

        # Excluded sources
        if exsources := q.get("exsources", []):
            ids = [item.get("id") for item in exsources]
            conditions.append(~Bulletin.sources.any(Source.id.in_(ids)))

        # Locations
        if locations := q.get("locations", []):
            ids = [item.get("id") for item in locations]
            if q.get("oplocations"):
                locs = (
                    db.session.query(Location.id)
                    .filter(or_(*[Location.id_tree.like("%[{}]%".format(x)) for x in ids]))
                    .all()
                )
                loc_ids = [loc.id for loc in locs]
                conditions.append(Bulletin.locations.any(Location.id.in_(loc_ids)))
            else:
                id_mix = [Location.get_children_by_id(id) for id in ids]
                conditions.extend(Bulletin.locations.any(Location.id.in_(i)) for i in id_mix)

        # Excluded locations
        if exlocations := q.get("exlocations", []):
            ids = [item.get("id") for item in exlocations]
            conditions.append(~Bulletin.locations.any(Location.id.in_(ids)))

        # Dates
        if pubdate := q.get("pubdate", None):
            conditions.append(date_between_query(Bulletin.publish_date, pubdate))

        if docdate := q.get("docdate", None):
            conditions.append(date_between_query(Bulletin.documentation_date, docdate))

        if created := q.get("created", None):
            conditions.append(date_between_query(Bulletin.created_at, created))

        if updated := q.get("updated", None):
            conditions.append(date_between_query(Bulletin.updated_at, updated))

        # Events
        single_event = q.get("singleEvent", None)
        event_dates = q.get("edate", None)
        event_type = q.get("etype", None)
        event_location = q.get("elocation", None)

        if event_dates or event_type or event_location:
            eventtype_id = event_type.get("id") if event_type else None
            event_location_id = event_location.get("id") if event_location else None
            event_conditions = Event.get_event_filters(
                dates=event_dates, eventtype_id=eventtype_id, event_location_id=event_location_id
            )
            if single_event:
                conditions.append(Bulletin.events.any(and_(*event_conditions)))
            else:
                conditions.extend(
                    [Bulletin.events.any(condition) for condition in event_conditions]
                )

        # Access Roles
        if roles := q.get("roles"):
            conditions.append(Bulletin.roles.any(Role.id.in_(roles)))
        if q.get("norole"):
            conditions.append(~Bulletin.roles.any())

        # Assignments
        if assigned := q.get("assigned", []):
            conditions.append(Bulletin.assigned_to_id.in_(assigned))

        if q.get("unassigned"):
            conditions.append(Bulletin.assigned_to == None)

        # First peer reviewer
        if fpr := q.get("reviewer", []):
            conditions.append(Bulletin.first_peer_reviewer_id.in_(fpr))

        # Workflow statuses
        if statuses := q.get("statuses", []):
            conditions.append(Bulletin.status.in_(statuses))

        # Review status
        if review_action := q.get("reviewAction", None):
            conditions.append(Bulletin.review_action == review_action)

        # Relations
        if rel_to_bulletin := q.get("rel_to_bulletin"):
            bulletin = db.session.query(Bulletin).get(int(rel_to_bulletin))
            if bulletin:
                ids = [b.get_other_id(bulletin.id) for b in bulletin.bulletin_relations]
                conditions.append(Bulletin.id.in_(ids))

        if rel_to_actor := q.get("rel_to_actor"):
            actor = db.session.query(Actor).get(int(rel_to_actor))
            if actor:
                ids = [b.bulletin_id for b in actor.bulletin_relations]
                conditions.append(Bulletin.id.in_(ids))

        if rel_to_incident := q.get("rel_to_incident"):
            incident = db.session.query(Incident).get(int(rel_to_incident))
            if incident:
                ids = [b.bulletin_id for b in incident.bulletin_relations]
                conditions.append(Bulletin.id.in_(ids))

        # Geospatial search
        loc_types = q.get("locTypes")
        latlng = q.get("latlng")

        if loc_types and latlng and (radius := latlng.get("radius")):
            geo_conditions = []
            if "locations" in loc_types:
                geo_conditions.append(Bulletin.geo_query_location(latlng, radius))
            if "geomarkers" in loc_types:
                geo_conditions.append(Bulletin.geo_query_geo_location(latlng, radius))
            if "events" in loc_types:
                geo_conditions.append(Bulletin.geo_query_event_location(latlng, radius))

            conditions.append(or_(*geo_conditions))

        if conditions:
            stmt = stmt.where(and_(*conditions))

        return stmt, conditions

    def location_query(self, q: dict) -> list:
        """
        Build a query for the location model.

        Args:
            - q: The search query.

        Returns:
            - A list of query conditions.
        """
        query = []

        # restrict parent search by admin level
        lvl = q.get("lvl")
        if lvl is not None:
            # this can throw exception
            try:
                lvl = int(lvl)
            except ValueError:
                # Handle the error or return, as 'lvl' should be an integer
                return None

            # Directly check if 'lvl' exists in the database and get the object (one query)
            admin_level = (
                db.session.query(LocationAdminLevel).filter(LocationAdminLevel.code == lvl).first()
            )

            if admin_level:
                # If the specific location type exists, add it to the query
                query.append(Location.admin_level == admin_level)

        if title := q.get("title"):
            words = title.split(" ")
            # search for bilingual title columns
            qsearch = [
                or_(
                    Location.title.ilike("%{}%".format(word)),
                    Location.title_ar.ilike("%{}%".format(word)),
                )
                for word in words
            ]

            query.extend(qsearch)

        if tsv := q.get("tsv"):
            words = tsv.split(" ")
            # search for bilingual title columns
            qsearch = [Location.description.ilike("%{}%".format(word)) for word in words]

            query.extend(qsearch)

        # point and radius search
        latlng = q.get("latlng")
        if latlng and (radius := latlng.get("radius")):
            query.append(Location.geo_query_location(latlng, radius))

        # handle location type search
        location_type = q.get("location_type")
        if location_type and (location_type_id := location_type.get("id")):
            query.append(Location.location_type_id == location_type_id)

        # admin levels
        admin_level = q.get("admin_level", None)
        if admin_level and (admin_level_id := admin_level.get("code")):
            query.append(Location.admin_level_id == admin_level_id)

        # country

        country = q.get("country", [])

        if country and (id := country.get("id")):
            query.append(Location.country_id == id)

        # tags
        tags = q.get("tags")
        if tags:
            search = ["%" + r + "%" for r in tags]
            # get search operator
            op = q.get("optags", False)
            if op:
                query.append(or_(func.array_to_string(Location.tags, "").ilike(r) for r in search))
            else:
                query.append(and_(func.array_to_string(Location.tags, "").ilike(r) for r in search))

        return query
