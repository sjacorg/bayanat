"""Smart-block registry for dossier export templates.

A template is an ordered list of ``{"id", "type", "config"}`` dicts
(ExportTemplate.blocks). Each block type registered here provides:

- a config validator (used on save and again on render), and
- a builder that turns (dossier data, config) into a plain render context.

All logic is deterministic code. Analyst-authored content is data: rich text
is sanitized with a strict dossier profile and nothing is ever evaluated as a
Jinja template.
"""

from datetime import datetime
from typing import Any, Callable, Optional

import bleach

from enferno.utils.logging_utils import get_logger

logger = get_logger()

MAX_BLOCKS = 50
MAX_TEXT = 20_000
MAX_TITLE = 500

# Strict profile for analyst-authored rich text inside dossiers: structural
# tags only, no links, no images, no styles. `dir` is allowed for mixed
# direction (RTL/LTR) content.
DOSSIER_TAGS = [
    "p",
    "br",
    "strong",
    "em",
    "u",
    "s",
    "ul",
    "ol",
    "li",
    "h2",
    "h3",
    "blockquote",
    "table",
    "tbody",
    "thead",
    "tr",
    "th",
    "td",
    "span",
]
DOSSIER_ATTRS = {"*": ["dir"]}


def sanitize_dossier_html(value: str) -> str:
    return bleach.clean(value or "", tags=DOSSIER_TAGS, attributes=DOSSIER_ATTRS, strip=True)


def _fmt_date(value: Any) -> Optional[str]:
    return value.strftime("%Y-%m-%d") if value else None


def _location_string(location) -> Optional[str]:
    if not location:
        return None
    return location.title_ar or location.full_location or location.title


def _id_numbers(actor) -> Optional[str]:
    """Format the id_number JSONB list, resolving type ids to their titles."""
    from enferno.admin.models import IDNumberType

    entries = [d for d in (actor.id_number or []) if isinstance(d, dict)]
    if not entries:
        return None
    types = {str(t.id): t.title_tr or t.title for t in IDNumberType.query.all()}
    return ", ".join(
        f"{types.get(str(d.get('type')), d.get('type', ''))}: {d.get('number', '')}".strip(": ")
        for d in entries
    )


# ---------------------------------------------------------------------------
# Field whitelist: the only actor data a field_table block can surface.
# Each entry: label (en), label_ar, getter(actor) -> display value.
# ---------------------------------------------------------------------------


def _profile(actor) -> Optional[Any]:
    profiles = actor.actor_profiles
    return profiles[0] if profiles else None


def _profile_attr(name: str) -> Callable:
    def getter(actor):
        profile = _profile(actor)
        return getattr(profile, name, None) if profile else None

    return getter


def _profile_date(name: str) -> Callable:
    getter = _profile_attr(name)
    return lambda actor: _fmt_date(getter(actor))


ACTOR_FIELDS: dict[str, dict] = {
    "id": {
        "label": "Database ID",
        "label_ar": "الرقم التعريفي حسب قاعدة البيانات",
        "get": lambda a: a.id,
    },
    "name": {"label": "Full name", "label_ar": "الاسم الكامل", "get": lambda a: a.name},
    "name_ar": {
        "label": "Full name (Arabic)",
        "label_ar": "الاسم الكامل",
        "get": lambda a: a.name_ar,
    },
    "nickname": {
        "label": "Other names",
        "label_ar": "الاسم/الأسماء الأخرى",
        "get": lambda a: a.nickname,
    },
    "nickname_ar": {
        "label": "Other names (Arabic)",
        "label_ar": "الاسم/الأسماء الأخرى",
        "get": lambda a: a.nickname_ar,
    },
    "father_name": {
        "label": "Father's name",
        "label_ar": "اسم الأب",
        "get": lambda a: a.father_name,
    },
    "father_name_ar": {
        "label": "Father's name (Arabic)",
        "label_ar": "اسم الأب",
        "get": lambda a: a.father_name_ar,
    },
    "mother_name": {
        "label": "Mother's name",
        "label_ar": "اسم الأم",
        "get": lambda a: a.mother_name,
    },
    "mother_name_ar": {
        "label": "Mother's name (Arabic)",
        "label_ar": "اسم الأم",
        "get": lambda a: a.mother_name_ar,
    },
    "sex": {"label": "Sex", "label_ar": "الجنس", "get": lambda a: a.sex},
    "age": {"label": "Age group", "label_ar": "الفئة العمرية", "get": lambda a: a.age},
    "civilian": {
        "label": "Civilian status",
        "label_ar": "الصفة المدنية",
        "get": lambda a: a.civilian,
    },
    "type": {"label": "Type", "label_ar": "النوع", "get": lambda a: a.type},
    "occupation": {"label": "Occupation", "label_ar": "المهنة", "get": lambda a: a.occupation},
    "occupation_ar": {
        "label": "Occupation (Arabic)",
        "label_ar": "المهنة",
        "get": lambda a: a.occupation_ar,
    },
    "position": {"label": "Position", "label_ar": "المنصب", "get": lambda a: a.position},
    "position_ar": {
        "label": "Position (Arabic)",
        "label_ar": "المنصب",
        "get": lambda a: a.position_ar,
    },
    "family_status": {
        "label": "Family status",
        "label_ar": "الحالة العائلية",
        "get": lambda a: a.family_status,
    },
    "no_children": {
        "label": "Number of children",
        "label_ar": "عدد الأولاد",
        "get": lambda a: a.no_children,
    },
    "origin_place": {
        "label": "Place of origin",
        "label_ar": "مكان الأصل",
        "get": lambda a: _location_string(a.origin_place),
    },
    "id_number": {
        "label": "ID numbers",
        "label_ar": "الأرقام الثبوتية",
        "get": lambda a: _id_numbers(a),
    },
    "tags": {
        "label": "Tags",
        "label_ar": "الوسوم",
        "get": lambda a: ", ".join(a.tags or []) or None,
    },
    # First-profile fields
    "originid": {
        "label": "Origin ID",
        "label_ar": "الرقم التعريفي المصدري",
        "get": _profile_attr("originid"),
    },
    "description": {
        "label": "Description",
        "label_ar": "الوصف",
        "get": _profile_attr("description"),
    },
    "publish_date": {
        "label": "Publish date",
        "label_ar": "تاريخ النشر",
        "get": _profile_date("publish_date"),
    },
    "documentation_date": {
        "label": "Documentation date",
        "label_ar": "تاريخ التوثيق",
        "get": _profile_date("documentation_date"),
    },
    "last_address": {
        "label": "Last address",
        "label_ar": "آخر عنوان معروف",
        "get": _profile_attr("last_address"),
    },
}

RELATED_ACTOR_COLUMNS = {
    "id": {"label": "Database ID", "label_ar": "الرقم التعريفي", "ltr": True},
    "name": {"label": "Full name", "label_ar": "الاسم الكامل"},
    "relation": {"label": "Relationship", "label_ar": "صلة القرابة"},
    "comment": {"label": "Notes", "label_ar": "ملاحظات"},
}

RELATED_BULLETIN_COLUMNS = {
    "id": {"label": "Database ID", "label_ar": "الرقم التسلسلي حسب قاعدة البيانات", "ltr": True},
    "title": {"label": "Title", "label_ar": "العنوان"},
    "originid": {"label": "Origin ID", "label_ar": "الرقم المصدري", "ltr": True},
    "sources": {"label": "Sources", "label_ar": "المصادر"},
    "publish_date": {"label": "Publish date", "label_ar": "تاريخ النشر", "ltr": True},
    "documentation_date": {
        "label": "Documentation date",
        "label_ar": "تاريخ توثيق الدليل",
        "ltr": True,
    },
    "comment": {"label": "Notes", "label_ar": "ملاحظات"},
}

EVENT_COLUMNS = {
    "date": {"label": "Date", "label_ar": "التاريخ", "ltr": True},
    "title": {"label": "Event", "label_ar": "الحدث"},
    "type": {"label": "Type", "label_ar": "النوع"},
    "location": {"label": "Location", "label_ar": "المكان"},
    "comments": {"label": "Notes", "label_ar": "ملاحظات"},
}


class DossierData:
    """Per-dossier data context, computed once and shared by all blocks.

    Related entities are filtered through ``user.can_access`` so no block can
    surface an item the requesting user cannot access directly.
    """

    def __init__(self, actor, user, locale: str = "ar"):
        self.actor = actor
        self.user = user
        self.locale = locale
        self._related_actors = None
        self._related_bulletins = None
        self._redacted_media = None

    @property
    def related_actors(self) -> list[dict]:
        if self._related_actors is None:
            rows = []
            for relation in self.actor.actor_relations:
                other = (
                    relation.actor_to if relation.actor_id == self.actor.id else relation.actor_from
                )
                if other is None or other.deleted or not self.user.can_access(other):
                    continue
                info = relation.relation_info
                # Relation labels are directional: `title` reads from actor_from
                # to actor_to, `reverse_title` the other way around.
                if relation.actor_id == self.actor.id:
                    label = info.get("title_tr") or info.get("title")
                else:
                    label = info.get("reverse_title_tr") or info.get("reverse_title")
                rows.append(
                    {
                        "id": other.id,
                        "name": other.name_ar or other.name,
                        "relation_id": relation.related_as,
                        "relation": label,
                        "comment": relation.comment,
                    }
                )
            self._related_actors = sorted(rows, key=lambda r: r["id"])
        return self._related_actors

    @property
    def related_bulletins(self) -> list[dict]:
        if self._related_bulletins is None:
            rows = []
            for relation in self.actor.bulletin_relations:
                bulletin = relation.bulletin
                if bulletin is None or bulletin.deleted or not self.user.can_access(bulletin):
                    continue
                rows.append(
                    {
                        "id": bulletin.id,
                        "title": bulletin.title,
                        "originid": bulletin.originid,
                        "sources": ", ".join(s.title for s in bulletin.sources) or None,
                        "publish_date": _fmt_date(bulletin.publish_date),
                        "documentation_date": _fmt_date(bulletin.documentation_date),
                        "comment": relation.comment,
                    }
                )
            self._related_bulletins = sorted(rows, key=lambda r: r["id"])
        return self._related_bulletins

    @property
    def redacted_media(self) -> dict:
        """Redacted renditions of evidence media, latest per original.

        Fails closed: only media produced by the redaction tool is surfaced.
        Originals without a redacted rendition are counted and reported as
        gaps, never embedded. Interim selection until media carries an
        explicit export-approved designation.
        """
        if self._redacted_media is None:
            items = []
            unredacted = 0
            for relation in self.actor.bulletin_relations:
                bulletin = relation.bulletin
                if bulletin is None or bulletin.deleted or not self.user.can_access(bulletin):
                    continue
                latest = {}
                original_ids = []
                for media in bulletin.medias:
                    redaction = media.redaction
                    if redaction is None:
                        original_ids.append(media.id)
                        continue
                    key = redaction.original_media_id or redaction.source_media_id
                    if key not in latest or media.id > latest[key].id:
                        latest[key] = media
                unredacted += sum(1 for mid in original_ids if mid not in latest)
                for media in sorted(latest.values(), key=lambda m: m.id):
                    title = (
                        media.title_ar if self.locale == "ar" else media.title
                    ) or media.title_ar
                    ref = (
                        f"الدليل رقم {bulletin.id}"
                        if self.locale == "ar"
                        else f"Evidence #{bulletin.id}"
                    )
                    items.append(
                        {
                            "file": media.media_file,
                            "is_image": (media.media_file_type or "").startswith("image/"),
                            "title": title,
                            "ref": ref,
                        }
                    )
            self._redacted_media = {"media": items, "unredacted": unredacted}
        return self._redacted_media


# ---------------------------------------------------------------------------
# Config validators. Each returns a normalized config or raises ValueError.
# ---------------------------------------------------------------------------


def _require_str(config: dict, key: str, max_len: int, required: bool = False) -> Optional[str]:
    value = config.get(key)
    if value is None or value == "":
        if required:
            raise ValueError(f"'{key}' is required")
        return None
    if not isinstance(value, str):
        raise ValueError(f"'{key}' must be a string")
    if len(value) > max_len:
        raise ValueError(f"'{key}' exceeds {max_len} characters")
    return value


def _validate_columns(config: dict, allowed: dict, default: list) -> list:
    columns = config.get("columns") or default
    if not isinstance(columns, list) or not columns:
        raise ValueError("'columns' must be a non-empty list")
    unknown = [c for c in columns if c not in allowed]
    if unknown:
        raise ValueError(f"Unknown columns: {unknown}")
    return columns


def _v_heading(config: dict) -> dict:
    return {
        "text": _require_str(config, "text", MAX_TITLE, required=True),
        "level": 1 if config.get("level") == 1 else 2,
    }


def _v_rich_text(config: dict) -> dict:
    html = _require_str(config, "html", MAX_TEXT, required=True)
    return {"html": sanitize_dossier_html(html)}


def _v_field_table(config: dict) -> dict:
    fields = config.get("fields")
    if not isinstance(fields, list) or not fields:
        raise ValueError("'fields' must be a non-empty list")
    if len(fields) > 30:
        raise ValueError("Too many fields (max 30)")
    unknown = [f for f in fields if f not in ACTOR_FIELDS and not str(f).startswith("dyn:")]
    if unknown:
        raise ValueError(f"Unknown fields: {unknown}")
    return {"title": _require_str(config, "title", MAX_TITLE), "fields": fields}


def _v_family_members(config: dict) -> dict:
    relation_ids = config.get("relation_ids") or []
    if not isinstance(relation_ids, list) or not all(isinstance(i, int) for i in relation_ids):
        raise ValueError("'relation_ids' must be a list of integers")
    return {
        "title": _require_str(config, "title", MAX_TITLE),
        "relation_ids": relation_ids,
        "columns": _validate_columns(
            config, RELATED_ACTOR_COLUMNS, ["id", "name", "relation", "comment"]
        ),
    }


def _v_events_timeline(config: dict) -> dict:
    order = config.get("order", "asc")
    if order not in ("asc", "desc"):
        raise ValueError("'order' must be 'asc' or 'desc'")
    return {
        "title": _require_str(config, "title", MAX_TITLE),
        "order": order,
        "columns": _validate_columns(config, EVENT_COLUMNS, ["date", "title", "comments"]),
    }


def _v_related_items(config: dict) -> dict:
    return {
        "title": _require_str(config, "title", MAX_TITLE),
        "columns": _validate_columns(
            config,
            RELATED_BULLETIN_COLUMNS,
            ["id", "title", "documentation_date", "comment"],
        ),
    }


def _v_narrative_box(config: dict) -> dict:
    field = config.get("field")
    if field and field not in ("description", "comments", "review"):
        raise ValueError("'field' must be one of description, comments, review")
    return {"title": _require_str(config, "title", MAX_TITLE), "field": field or None}


def _v_media_appendix(config: dict) -> dict:
    return {"title": _require_str(config, "title", MAX_TITLE)}


def _v_page_break(config: dict) -> dict:
    return {}


# ---------------------------------------------------------------------------
# Builders. Each returns the render context for its block; `missing` lists
# human-readable gaps surfaced in the completeness panel.
# ---------------------------------------------------------------------------


def _b_heading(data: DossierData, config: dict) -> dict:
    return {"text": config["text"], "level": config["level"], "missing": []}


def _b_rich_text(data: DossierData, config: dict) -> dict:
    return {"html": config["html"], "missing": []}


def _b_field_table(data: DossierData, config: dict) -> dict:
    actor = data.actor
    dynamic = actor.get_dynamic_fields() if hasattr(actor, "get_dynamic_fields") else {}
    rows, missing = [], []
    for key in config["fields"]:
        if key.startswith("dyn:"):
            name = key[4:]
            label, value = name.replace("_", " ").title(), dynamic.get(name)
        else:
            spec = ACTOR_FIELDS[key]
            label = spec["label_ar"] if data.locale == "ar" else spec["label"]
            value = spec["get"](actor)
        if value in (None, ""):
            missing.append(label)
        rows.append({"label": label, "value": value})
    return {"title": config.get("title"), "rows": rows, "missing": missing}


def _b_family_members(data: DossierData, config: dict) -> dict:
    relation_ids = config["relation_ids"]
    rows = [r for r in data.related_actors if not relation_ids or r["relation_id"] in relation_ids]
    columns = _labeled_columns(config["columns"], RELATED_ACTOR_COLUMNS, data.locale)
    missing = [] if rows else ["No related persons matched this table"]
    return {"title": config.get("title"), "columns": columns, "rows": rows, "missing": missing}


def _b_events_timeline(data: DossierData, config: dict) -> dict:
    events = sorted(
        data.actor.events,
        key=lambda e: e.from_date or e.to_date or datetime.min,
        reverse=config["order"] == "desc",
    )
    rows = [
        {
            "date": _fmt_date(e.from_date) or _fmt_date(e.to_date),
            "title": (e.title_ar if data.locale == "ar" else e.title) or e.title or e.title_ar,
            "type": e.eventtype.title if e.eventtype else None,
            "location": _location_string(e.location),
            "comments": (e.comments_ar if data.locale == "ar" else e.comments)
            or e.comments
            or e.comments_ar,
        }
        for e in events
    ]
    columns = _labeled_columns(config["columns"], EVENT_COLUMNS, data.locale)
    missing = [] if rows else ["No events recorded"]
    return {"title": config.get("title"), "columns": columns, "rows": rows, "missing": missing}


def _b_related_items(data: DossierData, config: dict) -> dict:
    columns = _labeled_columns(config["columns"], RELATED_BULLETIN_COLUMNS, data.locale)
    rows = data.related_bulletins
    missing = [] if rows else ["No related items"]
    return {"title": config.get("title"), "columns": columns, "rows": rows, "missing": missing}


def _b_narrative_box(data: DossierData, config: dict) -> dict:
    text = None
    if config["field"] == "description":
        profile = _profile(data.actor)
        text = profile.description if profile else None
        # description is rich text authored in the app; keep it but re-sanitize
        # with the dossier profile.
        text = sanitize_dossier_html(text) if text else None
    elif config["field"]:
        text = getattr(data.actor, config["field"], None)
    missing = (
        [f"Narrative '{config.get('title') or config['field'] or ''}' is empty"]
        if config["field"] and not text
        else []
    )
    return {
        "title": config.get("title"),
        "html": text,
        "is_html": config["field"] == "description",
        "missing": missing,
    }


def _b_media_appendix(data: DossierData, config: dict) -> dict:
    bundle = data.redacted_media
    missing = []
    if not bundle["media"]:
        missing.append("No redacted evidence media to attach")
    if bundle["unredacted"]:
        missing.append(
            f"{bundle['unredacted']} evidence media item(s) have no redacted rendition "
            "and were excluded"
        )
    return {"title": config["title"], "media": bundle["media"], "missing": missing}


def _b_page_break(data: DossierData, config: dict) -> dict:
    return {"missing": []}


def _labeled_columns(keys: list, spec: dict, locale: str) -> list[dict]:
    label_key = "label_ar" if locale == "ar" else "label"
    return [{"key": k, "label": spec[k][label_key], "ltr": bool(spec[k].get("ltr"))} for k in keys]


BLOCK_TYPES: dict[str, dict] = {
    "heading": {"validate": _v_heading, "build": _b_heading},
    "rich_text": {"validate": _v_rich_text, "build": _b_rich_text},
    "field_table": {"validate": _v_field_table, "build": _b_field_table},
    "family_members_table": {"validate": _v_family_members, "build": _b_family_members},
    "events_timeline": {"validate": _v_events_timeline, "build": _b_events_timeline},
    "related_items_table": {"validate": _v_related_items, "build": _b_related_items},
    "narrative_box": {"validate": _v_narrative_box, "build": _b_narrative_box},
    "media_appendix": {"validate": _v_media_appendix, "build": _b_media_appendix},
    "page_break": {"validate": _v_page_break, "build": _b_page_break},
}


def validate_blocks(blocks: Any) -> list[dict]:
    """Validate and normalize a template's block list. Raises ValueError."""
    if not isinstance(blocks, list):
        raise ValueError("'blocks' must be a list")
    if len(blocks) > MAX_BLOCKS:
        raise ValueError(f"Too many blocks (max {MAX_BLOCKS})")
    normalized = []
    for i, block in enumerate(blocks):
        if not isinstance(block, dict):
            raise ValueError(f"Block {i + 1} is not an object")
        block_type = block.get("type")
        if block_type not in BLOCK_TYPES:
            raise ValueError(f"Block {i + 1}: unknown type '{block_type}'")
        config = block.get("config") or {}
        if not isinstance(config, dict):
            raise ValueError(f"Block {i + 1}: config must be an object")
        try:
            config = BLOCK_TYPES[block_type]["validate"](config)
        except ValueError as e:
            raise ValueError(f"Block {i + 1} ({block_type}): {e}")
        normalized.append(
            {"id": str(block.get("id") or i + 1), "type": block_type, "config": config}
        )
    return normalized


def build_dossier(template, actor, user) -> dict:
    """Build the full render context for one dossier.

    The caller is responsible for authorizing `user` against `actor`;
    related entities are access-filtered here via DossierData.
    """
    blocks = validate_blocks(template.blocks or [])
    data = DossierData(actor, user)
    built, missing, section = [], [], 0
    for block in blocks:
        context = BLOCK_TYPES[block["type"]]["build"](data, block["config"])
        if block["type"] == "heading" and context["level"] == 2:
            section += 1
            context["number"] = section
        context["type"] = block["type"]
        built.append(context)
        missing.extend(context.get("missing") or [])
    return {
        "template": template,
        "actor": actor,
        "blocks": built,
        "missing": missing,
        "locale": "ar",
        "rtl": True,
    }
