import re
from dateutil.parser import parse
from sqlalchemy import or_, not_, and_, func, text, select, literal_column, bindparam
from sqlalchemy.sql.elements import BinaryExpression, ColumnElement
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime, time

from enferno.extensions import db
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
from enferno.admin.models.DynamicField import DynamicField
from enferno.user.models import Role
from enferno.utils.logging_utils import get_logger


logger = get_logger()


# helper methods


def date_between_query(field: ColumnElement, dates: list) -> BinaryExpression:
    """
    Create a date range query for a given field using proper timestamp ranges.

    This function converts user-provided dates to timestamp ranges that preserve
    database index usage, avoiding the performance penalty of function wrappers
    around indexed columns.

    Args:
        - field: The timestamp field to search on.
        - dates: A list of one or two dates in string format.

    Returns:
        - A binary expression for the date range query that uses indexes.
    """
    from datetime import datetime, time

    start_date = parse(dates[0]).date()
    if len(dates) == 1:
        end_date = start_date
    else:
        end_date = parse(dates[1]).date()

    # Convert dates to proper timestamp ranges
    # Start of day: 00:00:00.000000
    start_datetime = datetime.combine(start_date, time.min)
    # End of day: 23:59:59.999999 (use next day 00:00:00 exclusive)
    end_datetime = datetime.combine(end_date, time.max)

    return field.between(start_datetime, end_datetime)


class SearchUtils:
    """Utility class to build search queries for different models."""

    def __init__(self, q=None, cls=None):
        self.search = q
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

        elif self.cls == "actor":
            # Get conditions from first query
            main_stmt, conditions = self.actor_query(self.search[0])
            final_conditions = conditions

            # Handle nested queries by combining conditions
            if len(self.search) > 1:
                for i in range(1, len(self.search)):
                    _, next_conditions = self.actor_query(self.search[i])
                    op = self.search[i].get("op", "or")

                    if op == "and":
                        final_conditions.extend(next_conditions)
                    elif op == "or":
                        # Combine conditions with OR
                        final_conditions = [or_(*conditions, *next_conditions)]

            # Build final query with all conditions and default sorting
            result = select(Actor)
            if final_conditions:
                result = result.where(and_(*final_conditions))
            return result

        elif self.cls == "incident":
            # Get conditions from first query
            _, conditions = self.incident_query(self.search)
            # Build final query with all conditions and default sorting
            result = select(Incident)
            if conditions:
                result = result.where(and_(*conditions))
            return result

        elif self.cls == "location":
            return self.build_location_query()
        elif self.cls == "activity":
            return self.build_activity_query()
        return []

    def to_dict(self):
        """Return the search arguments."""
        return self.args

    def build_location_query(self):
        """Build a query for the location model."""
        return self.location_query(self.search)

    def build_activity_query(self):
        """Build a query for the activity model."""
        return self.activity_query(self.search)

    def _build_term_conditions(
        self, column: ColumnElement, terms: list, exact: bool = False, negate: bool = False
    ) -> list:
        """
        Build search conditions for multi-term text search.

        Args:
            column: The SQLAlchemy column to search on
            terms: List of search terms (each treated as a phrase)
            exact: If True, word boundary match; if False, substring match with wildcards
            negate: If True, negate conditions (for exclude)

        Returns:
            List of SQLAlchemy conditions

        Examples:
            exact=False: "open system" -> matches "reopen systems" (substring)
            exact=True:  "open system" -> matches "the open system" but not "reopen systems"
        """
        result = []
        for term in terms:
            if not term or not term.strip():
                continue

            term = term.strip()
            if exact:
                # Word boundary match - phrase as whole words (case-insensitive)
                # \y is PostgreSQL word boundary anchor
                escaped = re.escape(term)
                cond = column.op("~*")(f"\\y{escaped}\\y")
            else:
                # Phrase search with wildcards (default)
                cond = column.ilike(f"%{term}%")

            result.append(~cond if negate else cond)
        return result

    def _validate_dynamic_field_name(self, field_name: str, searchable_meta: dict) -> str:
        """
        Validate and sanitize a dynamic field name for SQL usage.

        This acts as a security barrier ensuring field names are safe SQL identifiers.
        Returns the validated field name or None if invalid.
        """
        if not field_name or field_name not in searchable_meta:
            return None
        # Ensure field name contains only safe characters (alphanumeric + underscore)
        if not field_name.replace("_", "").isalnum():
            return None
        return field_name

    def _apply_dynamic_field_filters(self, conditions: list, q: dict, entity_type: str):
        """
        Apply dynamic field filters to search conditions.

        Args:
            conditions: List of conditions to append to
            q: Search query dictionary
            entity_type: Entity type ('bulletin', 'incident', 'actor')
        """
        # Dynamic custom fields
        # Accept a permissive list of dicts under key "dyn"
        # Example: {"name": "case_number", "op": "contains", "value": "2024-"}
        try:
            dyn_filters = q.get("dyn", []) or []
            if isinstance(dyn_filters, list) and dyn_filters:
                # Preload searchable field meta for the entity type
                searchable_meta = {
                    f.name: f
                    for f in db.session.query(DynamicField)
                    .filter(
                        DynamicField.entity_type == entity_type,
                        DynamicField.active.is_(True),
                        DynamicField.searchable.is_(True),
                    )
                    .all()
                }

                def _coerce_text(raw):
                    if raw is None:
                        return ""
                    return str(raw).strip()

                def _normalize_select_values(raw):
                    if raw is None:
                        return []
                    if isinstance(raw, (list, tuple, set)):
                        return [str(v).strip() for v in raw if v is not None and str(v).strip()]
                    text_value = _coerce_text(raw)
                    return [text_value] if text_value else []

                for item in dyn_filters:
                    if not isinstance(item, dict):
                        logger.warning("dyn filter skipped: invalid item", extra={"item": item})
                        continue

                    # Validate and sanitize field name (acts as security barrier for CodeQL)
                    raw_name = item.get("name")
                    name = self._validate_dynamic_field_name(raw_name, searchable_meta)
                    if not name:
                        logger.warning(
                            "dyn filter skipped: invalid dynamic field name",
                            extra={"field_name": raw_name},
                        )
                        continue

                    op = (item.get("op") or "eq").lower()
                    value = item.get("value")
                    df = searchable_meta[name]
                    # Skip SQLAlchemy column check - use raw SQL for dynamic fields
                    # This avoids issues with dynamic columns not being in the model metadata

                    # Contains for TEXT and LONG_TEXT fields
                    if (
                        df.field_type
                        in (
                            DynamicField.TEXT,
                            DynamicField.LONG_TEXT,
                        )
                        and op == "contains"
                    ):
                        value_str = _coerce_text(value)
                        if value_str:
                            param_key = f"{name}_contains_{len(conditions)}"
                            conditions.append(
                                literal_column(name, type_=String()).ilike(
                                    bindparam(param_key, f"%{value_str}%")
                                )
                            )
                        continue

                    # NUMBER equality
                    if df.field_type == DynamicField.NUMBER and op == "eq":
                        try:
                            num = int(value) if value is not None else None
                            if num is not None:
                                param_key = f"{name}_eq_{len(conditions)}"
                                conditions.append(
                                    literal_column(name, type_=Integer())
                                    == bindparam(param_key, num)
                                )
                        except (TypeError, ValueError):
                            logger.warning(
                                "dyn filter number cast failed",
                                extra={"field": name, "value": value},
                            )
                        continue

                    # DATETIME between
                    if df.field_type == DynamicField.DATETIME and op == "between":
                        if isinstance(value, (list, tuple)) and len(value) >= 1:
                            dates = [d for d in value[:2] if d]
                            if dates:
                                start_date = parse(dates[0]).date()
                                end_date = parse(dates[1]).date() if len(dates) > 1 else start_date
                                start_datetime = datetime.combine(start_date, time.min)
                                end_datetime = datetime.combine(end_date, time.max)
                                suffix = len(conditions)
                                conditions.append(
                                    literal_column(name, type_=DateTime()).between(
                                        bindparam(f"{name}_start_{suffix}", start_datetime),
                                        bindparam(f"{name}_end_{suffix}", end_datetime),
                                    )
                                )
                        continue

                    # SELECT field operations
                    if df.field_type == DynamicField.SELECT:
                        values = _normalize_select_values(value)
                        array_col = literal_column(name, type_=ARRAY(String()))

                        if op == "contains":
                            lookup = values[0] if values else ""
                            if lookup:
                                param_key = f"{name}_contains_{len(conditions)}"
                                conditions.append(
                                    func.array_to_string(array_col, " ").ilike(
                                        bindparam(param_key, f"%{lookup}%")
                                    )
                                )
                        elif op == "eq":
                            if values:
                                param_key = f"{name}_eq_{len(conditions)}"
                                conditions.append(
                                    array_col.contains(
                                        bindparam(param_key, [values[0]], type_=ARRAY(String()))
                                    )
                                )
                        elif op == "any":
                            if values:
                                param_key = f"{name}_any_{len(conditions)}"
                                conditions.append(
                                    array_col.overlap(
                                        bindparam(param_key, values, type_=ARRAY(String()))
                                    )
                                )
                        elif op == "all":
                            if values:
                                param_key = f"{name}_all_{len(conditions)}"
                                conditions.append(
                                    array_col.contains(
                                        bindparam(param_key, values, type_=ARRAY(String()))
                                    )
                                )
                        continue

                    # Fallback: log unsupported operator
                    logger.warning(
                        "dyn filter skipped: unsupported operator",
                        extra={"field": name, "op": op, "field_type": df.field_type},
                    )

        except Exception as e:
            # Fail-safe: dynamic filters should never break search
            logger.warning("dyn filters evaluation failed", exc_info=e)

    def bulletin_query(self, q: dict):
        """Build a select statement for bulletin search"""
        conditions = []

        # Support query using a range of ids
        if ids := q.get("ids"):
            conditions.append(Bulletin.id.in_(ids))

        # Text search - PERFORMANCE OPTIMIZED
        if tsv := q.get("tsv"):
            words = tsv.split(" ")
            # Use individual ILIKE conditions instead of ILIKE ALL() to enable GIN trigram index usage
            # This changes execution from Sequential Scan to Bitmap Index Scan (200x faster)
            word_conditions = [Bulletin.search.ilike(f"%{word}%") for word in words if word.strip()]
            if word_conditions:
                conditions.extend(word_conditions)

        # exclude  filter - OPTIMIZED APPROACH using raw SQL
        extsv = q.get("extsv")
        if extsv:
            words = [word.strip() for word in extsv.split(" ") if word.strip()]
            if words:
                # Use raw SQL with NOT ILIKE ALL for optimal performance
                # This leverages the GIN trigram index efficiently
                exclude_patterns = [f"%{word}%" for word in words]
                placeholders = [f":exclude_{i}" for i in range(len(exclude_patterns))]
                array_sql = "ARRAY[" + ", ".join(placeholders) + "]"
                raw_condition = text(f"search NOT ILIKE ALL ({array_sql})")

                # Bind the parameters
                params = {f"exclude_{i}": pattern for i, pattern in enumerate(exclude_patterns)}
                raw_condition = raw_condition.bindparams(**params)

                conditions.append(raw_condition)

        # Origin ID
        originid = (q.get("originid") or "").strip()
        if originid:
            condition = Bulletin.originid.ilike(f"%{originid}%")
            conditions.append(condition)

        # Tags - OPTIMIZED APPROACH respecting UI checkboxes
        if ref := q.get("tags"):
            exact = q.get("inExact")  # "Exact Match" checkbox
            if exact:
                # User checked "Exact Match" - use fast array containment (9533x faster!)
                tag_conditions = [
                    text("tags @> ARRAY[:tag]::varchar[]").bindparams(tag=r) for r in ref
                ]
            else:
                # User wants partial matching - use ILIKE for wildcard behavior
                tag_conditions = [
                    func.array_to_string(Bulletin.tags, " ").ilike(f"%{r}%") for r in ref
                ]

            # "Any" checkbox controls AND vs OR between multiple tags
            if q.get("opTags", False):
                conditions.append(or_(*tag_conditions))
            else:
                conditions.append(and_(*tag_conditions))

        # Exclude tags
        if exref := q.get("exTags"):
            exact = q.get("exExact")
            if exact:
                tag_conditions = [
                    ~func.array_to_string(Bulletin.tags, " ").op("~*")(f"\\y{re.escape(r)}\\y")
                    for r in exref
                ]
            else:
                tag_conditions = [
                    ~func.array_to_string(Bulletin.tags, " ").ilike(f"%{r}%") for r in exref
                ]

            opexref = q.get("opExTags")
            if opexref:
                conditions.append(or_(*tag_conditions))
            else:
                conditions.append(and_(*tag_conditions))

        # Search Terms - chips-based multi-term text search
        if search_terms := q.get("searchTerms"):
            exact = q.get("termsExact", False)
            term_conds = self._build_term_conditions(Bulletin.search, search_terms, exact)
            if term_conds:
                if q.get("opTerms", False):
                    conditions.append(or_(*term_conds))
                else:
                    conditions.extend(term_conds)

        # Exclude Search Terms
        if ex_terms := q.get("exTerms"):
            exact = q.get("exTermsExact", False)
            ex_conds = self._build_term_conditions(Bulletin.search, ex_terms, exact, negate=True)
            if ex_conds:
                if q.get("opExTerms", False):
                    conditions.append(or_(*ex_conds))
                else:
                    conditions.extend(ex_conds)

        # Labels
        if labels := q.get("labels", []):
            ids = [item.get("id") for item in labels]
            recursive = q.get("childlabels", None)
            if q.get("oplabels"):
                if recursive:
                    result = db.session.scalars(select(Label).where(Label.id.in_(ids))).all()
                    direct = [label for label in result]
                    all_labels = direct + Label.get_children(direct)
                    all_labels = list(set(all_labels))
                    ids = [label.id for label in all_labels]
                conditions.append(Bulletin.labels.any(Label.id.in_(ids)))
            else:
                if recursive:
                    direct = db.session.scalars(select(Label).where(Label.id.in_(ids))).all()
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
                    result = db.session.scalars(select(Label).where(Label.id.in_(ids))).all()
                    direct = [label for label in result]
                    all_labels = direct + Label.get_children(direct)
                    all_labels = list(set(all_labels))
                    ids = [label.id for label in all_labels]
                conditions.append(Bulletin.ver_labels.any(Label.id.in_(ids)))
            else:
                if recursive:
                    direct = db.session.scalars(select(Label).where(Label.id.in_(ids))).all()
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
                    result = db.session.scalars(select(Source).where(Source.id.in_(ids))).all()
                    direct = [source for source in result]
                    all_sources = direct + Source.get_children(direct)
                    all_sources = list(set(all_sources))
                    ids = [source.id for source in all_sources]
                conditions.append(Bulletin.sources.any(Source.id.in_(ids)))
            else:
                if recursive:
                    direct = db.session.scalars(select(Source).where(Source.id.in_(ids))).all()
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
                locs = db.session.scalars(
                    select(Location.id).where(
                        or_(*[Location.id_tree.like("%[{}]%".format(x)) for x in ids])
                    )
                ).all()
                loc_ids = [loc for loc in locs]
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

        # Dynamic custom fields
        self._apply_dynamic_field_filters(conditions, q, "bulletin")

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
            bulletin = db.session.get(Bulletin, int(rel_to_bulletin))
            if bulletin:
                ids = [b.get_other_id(bulletin.id) for b in bulletin.bulletin_relations]
                conditions.append(Bulletin.id.in_(ids))

        if rel_to_actor := q.get("rel_to_actor"):
            actor = db.session.get(Actor, int(rel_to_actor))
            if actor:
                ids = [b.bulletin_id for b in actor.bulletin_relations]
                conditions.append(Bulletin.id.in_(ids))

        if rel_to_incident := q.get("rel_to_incident"):
            incident = db.session.get(Incident, int(rel_to_incident))
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

        # Use CTE to get matching IDs first
        matching_ids = (
            select(Bulletin.id)
            .where(and_(*conditions))
            .order_by(Bulletin.id.desc())
            .cte("matching_ids")
        )

        # Join with full bulletin data
        stmt = select(Bulletin).join(matching_ids, Bulletin.id == matching_ids.c.id)

        return stmt, conditions

    def actor_query(self, q: dict):
        """Build a select statement for actor search"""
        conditions = []

        # Support query using a range of ids
        if ids := q.get("ids"):
            conditions.append(Actor.id.in_(ids))

        # Text search - PERFORMANCE OPTIMIZED
        if tsv := q.get("tsv"):
            words = [word.strip() for word in tsv.split(" ") if word.strip()]
            if words:
                # For each word, create a condition that matches in either Actor.search OR ActorProfile.search
                qsearch = []
                for word in words:
                    qsearch.append(
                        or_(
                            Actor.search.ilike(f"%{word}%"),
                            ActorProfile.search.ilike(f"%{word}%"),
                        )
                    )

                subquery = select(Actor.id).join(Actor.actor_profiles).where(and_(*qsearch))
                conditions.append(Actor.id.in_(subquery))
        # Exclude text search
        if extsv := q.get("extsv"):
            cleaned_extsv = extsv.strip()
            if cleaned_extsv:
                if (
                    cleaned_extsv.startswith('"')
                    and cleaned_extsv.endswith('"')
                    and len(cleaned_extsv) > 2
                ):
                    # Remove quotes and treat as exact phrase
                    phrase = cleaned_extsv[1:-1].strip()
                    if phrase:
                        actor_exclude = Actor.search.notilike(f"%{phrase}%")
                        profile_exclude_subquery = (
                            select(Actor.id)
                            .join(Actor.actor_profiles)
                            .where(ActorProfile.search.ilike(f"%{phrase}%"))
                        )
                        profile_exclude = ~Actor.id.in_(profile_exclude_subquery)
                        conditions.extend([actor_exclude, profile_exclude])
                else:
                    # Split on spaces and exclude records containing ANY of these words
                    words = [word.strip() for word in cleaned_extsv.split() if word.strip()]
                    if words:
                        exclude_conditions = []
                        for word in words:
                            # Exclude if word matches in either Actor.search OR ActorProfile.search
                            exclude_conditions.append(
                                or_(
                                    Actor.search.ilike(f"%{word}%"),
                                    ActorProfile.search.ilike(f"%{word}%"),
                                )
                            )

                        # Create subquery to find actors that match ANY of the exclude conditions
                        subquery = (
                            select(Actor.id)
                            .join(Actor.actor_profiles)
                            .where(or_(*exclude_conditions))
                        )
                        conditions.append(~Actor.id.in_(subquery))

        # Search Terms - chips-based multi-term text search
        if search_terms := q.get("searchTerms"):
            exact = q.get("termsExact", False)
            term_conds = self._build_term_conditions(Actor.search, search_terms, exact)
            if term_conds:
                if q.get("opTerms", False):
                    conditions.append(or_(*term_conds))
                else:
                    conditions.extend(term_conds)

        # Exclude Search Terms
        if ex_terms := q.get("exTerms"):
            exact = q.get("exTermsExact", False)
            ex_conds = self._build_term_conditions(Actor.search, ex_terms, exact, negate=True)
            if ex_conds:
                if q.get("opExTerms", False):
                    conditions.append(or_(*ex_conds))
                else:
                    conditions.extend(ex_conds)

        # Origin ID
        originid = (q.get("originid") or "").strip()
        if originid:
            condition = Actor.actor_profiles.any(ActorProfile.originid.ilike(f"%{originid}%"))
            conditions.append(condition)

        # Nickname
        if search := q.get("nickname"):
            conditions.append(
                or_(Actor.nickname.ilike(f"%{search}%"), Actor.nickname_ar.ilike(f"%{search}%"))
            )

        # First name
        if search := q.get("first_name"):
            conditions.append(
                or_(Actor.first_name.ilike(f"%{search}%"), Actor.first_name_ar.ilike(f"%{search}%"))
            )

        # Middle name
        if search := q.get("middle_name"):
            conditions.append(
                or_(
                    Actor.middle_name.ilike(f"%{search}%"),
                    Actor.middle_name_ar.ilike(f"%{search}%"),
                )
            )

        # Last name
        if search := q.get("last_name"):
            conditions.append(
                or_(Actor.last_name.ilike(f"%{search}%"), Actor.last_name_ar.ilike(f"%{search}%"))
            )

        # Father name
        if search := q.get("father_name"):
            conditions.append(
                or_(
                    Actor.father_name.ilike(f"%{search}%"),
                    Actor.father_name_ar.ilike(f"%{search}%"),
                )
            )

        # Mother name
        if search := q.get("mother_name"):
            conditions.append(
                or_(
                    Actor.mother_name.ilike(f"%{search}%"),
                    Actor.mother_name_ar.ilike(f"%{search}%"),
                )
            )

        # Ethnography
        if ethno := q.get("ethnography"):
            ids = [item.get("id") for item in ethno]
            op = q.get("opEthno")
            if op:
                conditions.append(Actor.ethnographies.any(Ethnography.id.in_(ids)))
            else:
                conditions.extend([Actor.ethnographies.any(Ethnography.id == id) for id in ids])

        # Nationality
        if nationality := q.get("nationality"):
            ids = [item.get("id") for item in nationality]
            op = q.get("opNat")
            if op:
                conditions.append(Actor.nationalities.any(Country.id.in_(ids)))
            else:
                conditions.extend([Actor.nationalities.any(Country.id == id) for id in ids])

        # Labels
        if labels := q.get("labels"):
            recursive = q.get("childlabels", None)
            ids = [item.get("id") for item in labels]
            if q.get("oplabels"):
                if recursive:
                    # get ids of children // update ids
                    result = db.session.scalars(select(Label).where(Label.id.in_(ids))).all()
                    direct = [label for label in result]
                    all_labels = direct + Label.get_children(direct)
                    all_labels = list(set(all_labels))
                    ids = [label.id for label in all_labels]
                conditions.append(
                    Actor.actor_profiles.any(ActorProfile.labels.any(Label.id.in_(ids)))
                )
            else:
                if recursive:
                    direct = db.session.scalars(select(Label).where(Label.id.in_(ids))).all()
                    for label in direct:
                        children = Label.get_children([label])
                        # add original label + uniquify list
                        children = list(set([label] + children))
                        ids = [child.id for child in children]
                        conditions.append(
                            Actor.actor_profiles.any(ActorProfile.labels.any(Label.id.in_(ids)))
                        )
                else:
                    conditions.extend(
                        [
                            Actor.actor_profiles.any(ActorProfile.labels.any(Label.id == id))
                            for id in ids
                        ]
                    )

        # Excluded labels
        if exlabels := q.get("exlabels"):
            ids = [item.get("id") for item in exlabels]
            conditions.append(~Actor.actor_profiles.any(ActorProfile.labels.any(Label.id.in_(ids))))

        # Verification labels
        if vlabels := q.get("vlabels"):
            ids = [item.get("id") for item in vlabels]
            recursive = q.get("childverlabels", None)
            if q.get("opvlabels"):
                # or operator
                if recursive:
                    # get ids of children // update ids
                    result = db.session.scalars(select(Label).where(Label.id.in_(ids))).all()
                    direct = [label for label in result]
                    all_labels = direct + Label.get_children(direct)
                    all_labels = list(set(all_labels))
                    ids = [label.id for label in all_labels]
                conditions.append(
                    Actor.actor_profiles.any(ActorProfile.ver_labels.any(Label.id.in_(ids)))
                )
            else:
                # and operator (modify children search logic)
                if recursive:
                    direct = db.session.scalars(select(Label).where(Label.id.in_(ids))).all()
                    for label in direct:
                        children = Label.get_children([label])
                        # add original label + uniquify list
                        children = list(set([label] + children))
                        ids = [child.id for child in children]
                        conditions.append(
                            Actor.actor_profiles.any(ActorProfile.ver_labels.any(Label.id.in_(ids)))
                        )
                else:
                    conditions.extend(
                        [
                            Actor.actor_profiles.any(ActorProfile.ver_labels.any(Label.id == id))
                            for id in ids
                        ]
                    )

        # Excluded vlabels
        if exvlabels := q.get("exvlabels"):
            ids = [item.get("id") for item in exvlabels]
            conditions.append(
                ~Actor.actor_profiles.any(ActorProfile.ver_labels.any(Label.id.in_(ids)))
            )

        # Sources
        if sources := q.get("sources"):
            ids = [item.get("id") for item in sources]
            # children search ?
            recursive = q.get("childsources", None)
            if q.get("opsources"):
                if recursive:
                    # get ids of children // update ids
                    result = db.session.scalars(select(Source).where(Source.id.in_(ids))).all()
                    direct = [source for source in result]
                    all_sources = direct + Source.get_children(direct)
                    all_sources = list(set(all_sources))
                    ids = [source.id for source in all_sources]
                conditions.append(
                    Actor.actor_profiles.any(ActorProfile.sources.any(Source.id.in_(ids)))
                )
            else:
                # and operator (modify children search logic)
                if recursive:
                    direct = db.session.scalars(select(Source).where(Source.id.in_(ids))).all()
                    for source in direct:
                        children = Source.get_children([source])
                        # add original label + uniquify list
                        children = list(set([source] + children))
                        ids = [child.id for child in children]
                        conditions.append(
                            Actor.actor_profiles.any(ActorProfile.sources.any(Source.id.in_(ids)))
                        )
                else:
                    conditions.extend(
                        [
                            Actor.actor_profiles.any(ActorProfile.sources.any(Source.id == id))
                            for id in ids
                        ]
                    )

        # Excluded sources
        if exsources := q.get("exsources"):
            ids = [item.get("id") for item in exsources]
            conditions.append(
                ~Actor.actor_profiles.any(ActorProfile.sources.any(Source.id.in_(ids)))
            )

        # Tags
        if tags := q.get("tags"):
            exact = q.get("inExact")
            if exact:
                tag_conditions = [
                    func.array_to_string(Actor.tags, " ").op("~*")(f"\\y{re.escape(r)}\\y")
                    for r in tags
                ]
            else:
                tag_conditions = [
                    func.array_to_string(Actor.tags, " ").ilike(f"%{r}%") for r in tags
                ]

            # any operator
            op = q.get("opTags", False)
            if op:
                conditions.append(or_(*tag_conditions))
            else:
                conditions.append(and_(*tag_conditions))

        # Exclude tags
        if extags := q.get("exTags"):
            exact = q.get("exExact")
            if exact:
                tag_conditions = [
                    ~func.array_to_string(Actor.tags, " ").op("~*")(f"\\y{re.escape(r)}\\y")
                    for r in extags
                ]
            else:
                tag_conditions = [
                    ~func.array_to_string(Actor.tags, " ").ilike(f"%{r}%") for r in extags
                ]

            # get all operator
            opextags = q.get("opExTags")
            if opextags:
                conditions.append(or_(*tag_conditions))
            else:
                conditions.append(and_(*tag_conditions))

        # Residence locations
        if res_locations := q.get("resLocations", []):
            ids = [item.get("id") for item in res_locations]
            # get all child locations
            locs = db.session.scalars(
                select(Location.id).where(
                    or_(*[Location.id_tree.like("%[{}]%".format(x)) for x in ids])
                )
            ).all()
            loc_ids = [loc for loc in locs]
            # TODO: residence_place_id is not a valid column in the Actor model. Discuss with team.
            conditions.append(Actor.residence_place_id.in_(loc_ids))

        # Origin locations
        if origin_locations := q.get("originLocations", []):
            ids = [item.get("id") for item in origin_locations]
            # get all child locations
            locs = db.session.scalars(
                select(Location.id).where(
                    or_(*[Location.id_tree.like("%[{}]%".format(x)) for x in ids])
                )
            ).all()
            loc_ids = [loc for loc in locs]
            conditions.append(Actor.origin_place_id.in_(loc_ids))

        # Excluded residence locations
        if ex_res_locations := q.get("exResLocations", []):
            ids = [item.get("id") for item in ex_res_locations]
            conditions.append(~Actor.residence_place.has(Location.id.in_(ids)))

        # Excluded origin locations
        if ex_origin_locations := q.get("exOriginLocations", []):
            ids = [item.get("id") for item in ex_origin_locations]
            conditions.append(~Actor.origin_place.has(Location.id.in_(ids)))

        # Publish date
        if pubdate := q.get("pubdate", None):
            conditions.append(
                Actor.actor_profiles.any(date_between_query(ActorProfile.publish_date, pubdate))
            )

        # Documentation date
        if docdate := q.get("docdate", None):
            conditions.append(
                Actor.actor_profiles.any(
                    date_between_query(ActorProfile.documentation_date, docdate)
                )
            )

        # Creation date
        if created := q.get("created", None):
            conditions.append(date_between_query(Actor.created_at, created))

        # Modified date
        if updated := q.get("updated", None):
            conditions.append(date_between_query(Actor.updated_at, updated))

        # Event search
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
                conditions.append(Actor.events.any(and_(*event_conditions)))
            else:
                conditions.extend([Actor.events.any(condition) for condition in event_conditions])

        # Access Roles
        if roles := q.get("roles"):
            conditions.append(Actor.roles.any(Role.id.in_(roles)))
        if q.get("norole"):
            conditions.append(~Actor.roles.any())

        # Assigned user(s)
        if assigned := q.get("assigned", []):
            conditions.append(Actor.assigned_to_id.in_(assigned))

        # First peer reviewer
        if fpr := q.get("reviewer", []):
            conditions.append(Actor.first_peer_reviewer_id.in_(fpr))

        # Workflow status(s)
        if statuses := q.get("statuses", []):
            conditions.append(Actor.status.in_(statuses))

        # Review status
        if review_action := q.get("reviewAction", None):
            conditions.append(Actor.review_action == review_action)

        # Geospatial search
        loc_types = q.get("locTypes")
        latlng = q.get("latlng")

        if loc_types and latlng and (radius := latlng.get("radius")):
            geo_conditions = []
            if "originplace" in loc_types:
                geo_conditions.append(Actor.geo_query_origin_place(latlng, radius))
            if "events" in loc_types:
                geo_conditions.append(Actor.geo_query_event_location(latlng, radius))

            conditions.append(or_(*geo_conditions))

        # ---------- Extra fields -------------

        # Occupation
        if occupation := q.get("occupation", None):
            search = "%{}%".format(occupation)
            conditions.append(
                or_(Actor.occupation.ilike(search), Actor.occupation_ar.ilike(search))
            )

        # Position
        if position := q.get("position", None):
            search = "%{}%".format(position)
            conditions.append(or_(Actor.position.ilike(search), Actor.position_ar.ilike(search)))

        # Spoken Dialects
        if dialects := q.get("dialects", None):
            op = q.get("opDialects")
            ids = [item.get("id") for item in dialects]
            if op:
                conditions.append(Actor.dialects.any(Dialect.id.in_(ids)))
            else:
                conditions.extend([Actor.dialects.any(Dialect.id == id) for id in ids])

        # Family Status
        if family_status := q.get("family_status", None):
            conditions.append(Actor.family_status == family_status)

        # Sex
        if sex := q.get("sex", None):
            conditions.append(Actor.sex == sex)

        # Age
        if age := q.get("age", None):
            conditions.append(Actor.age == age)

        # Civilian
        if civilian := q.get("civilian", None):
            conditions.append(Actor.civilian == civilian)

        # Actor type
        if type_value := q.get("type", None):
            conditions.append(Actor.type == type_value)

        # ID Number search - using JSONB containment operators for efficiency
        id_number = q.get("id_number", None)
        if id_number and isinstance(id_number, dict):
            type_value = id_number.get("type", "").strip()
            number_value = id_number.get("number", "").strip()

            if type_value and number_value:
                # Both provided - use direct SQL with ILIKE for flexible matching
                conditions.append(
                    text(
                        "EXISTS (SELECT 1 FROM jsonb_array_elements(id_number) elem WHERE elem->>'type' = :type AND elem->>'number' ILIKE :number)"
                    ).bindparams(type=type_value, number=f"%{number_value}%")
                )
            elif type_value:
                # Type only - use containment operator
                conditions.append(Actor.id_number.op("@>")([{"type": type_value}]))
            elif number_value:
                # Number only - use jsonb_path_exists for ILIKE behavior
                path = f'$[*] ? (@.number like_regex "{number_value}" flag "i")'
                conditions.append(func.jsonb_path_exists(Actor.id_number, path))

        # Dynamic custom fields
        self._apply_dynamic_field_filters(conditions, q, "actor")

        # Related to bulletin search
        if rel_to_bulletin := q.get("rel_to_bulletin"):
            bulletin = db.session.get(Bulletin, int(rel_to_bulletin))
            if bulletin:
                ids = [a.actor_id for a in bulletin.actor_relations]
                conditions.append(Actor.id.in_(ids))

        # Related to actor search
        if rel_to_actor := q.get("rel_to_actor"):
            actor = db.session.get(Actor, int(rel_to_actor))
            if actor:
                ids = [a.get_other_id(actor.id) for a in actor.actor_relations]
                conditions.append(Actor.id.in_(ids))

        # Related to incident search
        if rel_to_incident := q.get("rel_to_incident"):
            incident = db.session.get(Incident, int(rel_to_incident))
            if incident:
                ids = [a.actor_id for a in incident.actor_relations]
                conditions.append(Actor.id.in_(ids))

        # Use CTE to get matching IDs first
        matching_ids = (
            select(Actor.id).where(and_(*conditions)).order_by(Actor.id.desc()).cte("matching_ids")
        )

        # Join with full actor data
        stmt = select(Actor).join(matching_ids, Actor.id == matching_ids.c.id)

        return stmt, conditions

    def incident_query(self, q: dict):
        """Build a select statement for incident search"""
        conditions = []

        # Support query using a range of ids
        if ids := q.get("ids"):
            conditions.append(Incident.id.in_(ids))

        # Text search - PERFORMANCE OPTIMIZED
        if tsv := q.get("tsv"):
            words = tsv.split(" ")
            # Use individual ILIKE conditions instead of ILIKE ALL() to enable GIN trigram index usage
            word_conditions = [Incident.search.ilike(f"%{word}%") for word in words if word.strip()]
            if word_conditions:
                conditions.extend(word_conditions)

        # exclude  filter - OPTIMIZED APPROACH
        extsv = q.get("extsv")
        if extsv:
            words = extsv.split(" ")
            # Use individual indexed searches instead of notilike(all_())
            exclude_conditions = []
            for word in words:
                exclude_conditions.append(Incident.search.ilike(f"%{word}%"))

            # Create subquery of IDs to exclude using individual indexed searches
            if exclude_conditions:
                exclude_subquery = select(Incident.id).where(or_(*exclude_conditions))
                conditions.append(~Incident.id.in_(exclude_subquery))

        # Search Terms - chips-based multi-term text search
        if search_terms := q.get("searchTerms"):
            exact = q.get("termsExact", False)
            term_conds = self._build_term_conditions(Incident.search, search_terms, exact)
            if term_conds:
                if q.get("opTerms", False):
                    conditions.append(or_(*term_conds))
                else:
                    conditions.extend(term_conds)

        # Exclude Search Terms
        if ex_terms := q.get("exTerms"):
            exact = q.get("exTermsExact", False)
            ex_conds = self._build_term_conditions(Incident.search, ex_terms, exact, negate=True)
            if ex_conds:
                if q.get("opExTerms", False):
                    conditions.append(or_(*ex_conds))
                else:
                    conditions.extend(ex_conds)

        # Labels
        if labels := q.get("labels", []):
            ids = [item.get("id") for item in labels]
            if q.get("oplabels"):
                conditions.append(Incident.labels.any(Label.id.in_(ids)))
            else:
                conditions.extend([Incident.labels.any(Label.id == id) for id in ids])

        # Excluded labels
        if exlabels := q.get("exlabels", []):
            ids = [item.get("id") for item in exlabels]
            conditions.append(~Incident.labels.any(Label.id.in_(ids)))

        # Verified labels
        if vlabels := q.get("vlabels", []):
            ids = [item.get("id") for item in vlabels]
            if q.get("opvlabels"):
                # And query
                conditions.append(Incident.ver_labels.any(Label.id.in_(ids)))
            else:
                conditions.extend([Incident.ver_labels.any(Label.id == id) for id in ids])

        # Excluded verified labels
        if exvlabels := q.get("exvlabels", []):
            ids = [item.get("id") for item in exvlabels]
            conditions.append(~Incident.ver_labels.any(Label.id.in_(ids)))

        # Sources
        if sources := q.get("sources", []):
            ids = [item.get("id") for item in sources]
            if q.get("opsources"):
                conditions.append(Incident.sources.any(Source.id.in_(ids)))
            else:
                conditions.extend([Incident.sources.any(Source.id == id) for id in ids])

        # Excluded sources
        if exsources := q.get("exsources", []):
            ids = [item.get("id") for item in exsources]
            conditions.append(~Incident.sources.any(Source.id.in_(ids)))

        # Locations
        if locations := q.get("locations", []):
            ids = [item.get("id") for item in locations]
            if q.get("oplocations"):
                # get all child locations
                locs = db.session.scalars(
                    select(Location.id).where(
                        or_(*[Location.id_tree.like("%[{}]%".format(x)) for x in ids])
                    )
                ).all()
                loc_ids = [loc for loc in locs]
                conditions.append(Incident.locations.any(Location.id.in_(loc_ids)))
            else:
                # get combined lists of ids for each location
                id_mix = [Location.get_children_by_id(id) for id in ids]
                conditions.extend(Incident.locations.any(Location.id.in_(i)) for i in id_mix)

        # Excluded locations
        if exlocations := q.get("exlocations", []):
            ids = [item.get("id") for item in exlocations]
            conditions.append(~Incident.locations.any(Location.id.in_(ids)))

        # Dates
        if created := q.get("created", None):
            conditions.append(date_between_query(Incident.created_at, created))

        if updated := q.get("updated", None):
            conditions.append(date_between_query(Incident.updated_at, updated))

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
                conditions.append(Incident.events.any(and_(*event_conditions)))
            else:
                conditions.extend(
                    [Incident.events.any(condition) for condition in event_conditions]
                )

        # Access Roles
        if roles := q.get("roles"):
            conditions.append(Incident.roles.any(Role.id.in_(roles)))
        if q.get("norole"):
            conditions.append(~Incident.roles.any())

        # Assignments
        if assigned := q.get("assigned", []):
            conditions.append(Incident.assigned_to_id.in_(assigned))

        # First peer reviewer
        if fpr := q.get("reviewer", []):
            conditions.append(Incident.first_peer_reviewer_id.in_(fpr))

        # Workflow statuses
        if statuses := q.get("statuses", []):
            conditions.append(Incident.status.in_(statuses))

        # Review status
        if review_action := q.get("reviewAction", None):
            conditions.append(Incident.review_action == review_action)

        # Potential violation categories
        if potential_violation_ids := q.get("potentialVCats", None):
            conditions.append(
                Incident.potential_violations.any(
                    PotentialViolation.id.in_(potential_violation_ids)
                )
            )

        # Claimed violation categories
        if claimed_violation_ids := q.get("claimedVCats", None):
            conditions.append(
                Incident.claimed_violations.any(ClaimedViolation.id.in_(claimed_violation_ids))
            )

        # Dynamic custom fields
        self._apply_dynamic_field_filters(conditions, q, "incident")

        # Relations
        if rel_to_bulletin := q.get("rel_to_bulletin"):
            bulletin = db.session.get(Bulletin, int(rel_to_bulletin))
            if bulletin:
                ids = [i.incident_id for i in bulletin.incident_relations]
                conditions.append(Incident.id.in_(ids))

        if rel_to_actor := q.get("rel_to_actor"):
            actor = db.session.get(Actor, int(rel_to_actor))
            if actor:
                ids = [i.incident_id for i in actor.incident_relations]
                conditions.append(Incident.id.in_(ids))

        if rel_to_incident := q.get("rel_to_incident"):
            incident = db.session.get(Incident, int(rel_to_incident))
            if incident:
                ids = [i.get_other_id(incident.id) for i in incident.incident_relations]
                conditions.append(Incident.id.in_(ids))

        # Use CTE to get matching IDs first
        matching_ids = (
            select(Incident.id)
            .where(and_(*conditions))
            .order_by(Incident.id.desc())
            .cte("matching_ids")
        )

        # Join with full incident data
        stmt = select(Incident).join(matching_ids, Incident.id == matching_ids.c.id)

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
            admin_level = db.session.scalar(
                select(LocationAdminLevel).where(LocationAdminLevel.code == lvl)
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

    def activity_query(self, q: dict) -> list:
        """
        Build a query for the activity model.

        Args:
            - q: The search query.

        Returns:
            - A list of query conditions.
        """
        query = []

        # Filtering by user_id
        if user_id := q.get("user"):
            query.append(Activity.user_id == user_id)

        # Use strict matching for action
        if action := q.get("action"):
            query.append(Activity.action == action)

        # Use strict matching for tag
        if model := q.get("model"):
            query.append(Activity.model == model)

        # activity date
        if created := q.get("created", None):
            query.append(date_between_query(Activity.created_at, created))

        return query
