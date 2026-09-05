"""Unit tests for the dossier export template block registry.

These are pure-function tests: block validation, sanitization, and dossier
building against lightweight fake entities (no database)."""

import pytest

from enferno.export.blocks import (
    MAX_BLOCKS,
    RELATIVE_FIELDS,
    build_dossier,
    sanitize_dossier_html,
    validate_blocks,
)


class FakeActor:
    __tablename__ = "actor"

    id = 42
    name = "John Doe"
    name_ar = "جون دو"
    nickname = None
    father_name = "Adam"
    sex = "Male"
    deleted = False
    actor_profiles = []
    events = []
    actors_to = []
    actors_from = []
    related_bulletins = []

    @property
    def actor_relations(self):
        return self.actors_to + self.actors_from

    @property
    def bulletin_relations(self):
        return self.related_bulletins

    def get_dynamic_fields(self):
        return {}


class FakeUser:
    def can_access(self, obj):
        return True


class FakeTemplate:
    title = "Test dossier"
    entity_type = "actor"

    def __init__(self, blocks):
        self.blocks = blocks


# --- validation -------------------------------------------------------------


def test_validate_blocks_rejects_non_list():
    with pytest.raises(ValueError):
        validate_blocks("not a list")


def test_validate_blocks_rejects_unknown_type():
    with pytest.raises(ValueError, match="unknown type"):
        validate_blocks([{"type": "evil_block", "config": {}}])


def test_validate_blocks_rejects_too_many():
    blocks = [{"type": "page_break", "config": {}}] * (MAX_BLOCKS + 1)
    with pytest.raises(ValueError, match="Too many blocks"):
        validate_blocks(blocks)


def test_validate_blocks_rejects_unknown_field_keys():
    with pytest.raises(ValueError, match="Unknown fields"):
        validate_blocks([{"type": "field_table", "config": {"fields": ["password_hash"]}}])


def test_validate_blocks_normalizes_and_drops_extra_keys():
    result = validate_blocks(
        [{"type": "heading", "config": {"text": "Title", "level": 1, "evil": "x"}, "junk": 1}]
    )
    assert result == [{"id": "1", "type": "heading", "config": {"text": "Title", "level": 1}}]


def test_validate_blocks_requires_heading_text():
    with pytest.raises(ValueError, match="'text' is required"):
        validate_blocks([{"type": "heading", "config": {}}])


def test_validate_blocks_rejects_unknown_columns():
    with pytest.raises(ValueError, match="Unknown columns"):
        validate_blocks([{"type": "related_items_table", "config": {"columns": ["id", "secret"]}}])


# --- sanitization -----------------------------------------------------------


def test_sanitizer_strips_scripts_links_images_and_styles():
    dirty = (
        '<p style="color:red">ok</p><script>alert(1)</script><img src="x"><a href="http://x">l</a>'
    )
    clean = sanitize_dossier_html(dirty)
    assert "<script" not in clean
    assert "<img" not in clean
    assert "<a" not in clean
    assert "style=" not in clean
    assert "ok" in clean


def test_rich_text_is_sanitized_at_validation_time():
    result = validate_blocks(
        [{"type": "rich_text", "config": {"html": "<p>hi</p><script>x()</script>"}}]
    )
    assert "<script" not in result[0]["config"]["html"]


# --- building ---------------------------------------------------------------


def test_build_dossier_field_table_and_missing():
    template = FakeTemplate(
        [
            {"type": "heading", "config": {"text": "برنامج الأشخاص المفقودين", "level": 1}},
            {"type": "heading", "config": {"text": "المعلومات التعريفية", "level": 2}},
            {"type": "field_table", "config": {"fields": ["name", "nickname", "sex"]}},
        ]
    )
    context = build_dossier(template, FakeActor(), FakeUser())

    assert context["rtl"] is True
    heading, section, table = context["blocks"]
    assert "number" not in heading  # level-1 title is not numbered
    assert section["number"] == 1  # numbered sections start at 1
    rows = {r["label"]: r["value"] for r in table["rows"]}
    assert rows["الاسم الكامل"] == "John Doe"
    # nickname is empty -> flagged in the completeness report
    assert "الاسم/الأسماء الأخرى" in context["missing"]


def test_build_dossier_empty_relations_flagged():
    template = FakeTemplate(
        [
            {"type": "family_members_table", "config": {}},
            {"type": "events_timeline", "config": {}},
        ]
    )
    context = build_dossier(template, FakeActor(), FakeUser())
    assert "No related persons matched this table" in context["missing"]
    assert "No events recorded" in context["missing"]


def test_build_dossier_revalidates_stored_blocks():
    template = FakeTemplate([{"type": "field_table", "config": {"fields": ["password_hash"]}}])
    with pytest.raises(ValueError):
        build_dossier(template, FakeActor(), FakeUser())


def _fake_media(**kwargs):
    from types import SimpleNamespace as NS

    defaults = {"redaction": None, "dossier": False}
    return NS(**{**defaults, **kwargs})


def test_media_appendix_fails_closed():
    """Only redaction results are surfaced; bare originals are excluded and flagged."""
    from types import SimpleNamespace as NS

    original = _fake_media(id=1)
    redacted = _fake_media(
        id=2,
        redaction=NS(original_media_id=1, source_media_id=1),
        media_file="doc-redacted.jpg",
        media_file_type="image/jpeg",
        title="doc",
        title_ar="وثيقة",
    )
    bare = _fake_media(id=3)
    bulletin = NS(id=75, deleted=False, medias=[original, redacted, bare])

    actor = FakeActor()
    actor.related_bulletins = [NS(bulletin=bulletin)]
    template = FakeTemplate([{"type": "media_appendix", "config": {}}])
    context = build_dossier(template, actor, FakeUser())

    block = context["blocks"][0]
    assert [m["file"] for m in block["media"]] == ["doc-redacted.jpg"]
    assert block["media"][0]["title"] == "وثيقة"
    assert any("no redacted rendition" in m for m in context["missing"])


def test_media_appendix_dossier_flag_is_authoritative():
    """Flagged media wins over the heuristic: an unflagged redaction is dropped,
    a flagged clean original is included, and no gap is reported."""
    from types import SimpleNamespace as NS

    original = _fake_media(id=1)
    redacted = _fake_media(
        id=2,
        redaction=NS(original_media_id=1, source_media_id=1),
        media_file="doc-redacted.jpg",
        media_file_type="image/jpeg",
        title="doc",
        title_ar="وثيقة",
    )
    clean = _fake_media(
        id=3,
        dossier=True,
        media_file="clean-original.jpg",
        media_file_type="image/jpeg",
        title="clean",
        title_ar="أصلية",
    )
    bulletin = NS(id=75, deleted=False, medias=[original, redacted, clean])

    actor = FakeActor()
    actor.related_bulletins = [NS(bulletin=bulletin)]
    template = FakeTemplate([{"type": "media_appendix", "config": {}}])
    context = build_dossier(template, actor, FakeUser())

    block = context["blocks"][0]
    assert [m["file"] for m in block["media"]] == ["clean-original.jpg"]
    assert context["missing"] == []


def test_narrative_box_rejects_workflow_fields(monkeypatch):
    monkeypatch.setattr(
        "enferno.export.blocks.narrative_fields",
        lambda: {"dossier_notes": "Dossier notes"},
    )
    for field in ("comments", "review"):
        with pytest.raises(ValueError):
            validate_blocks([{"type": "narrative_box", "config": {"title": "x", "field": field}}])
    ok = validate_blocks(
        [{"type": "narrative_box", "config": {"title": "x", "field": "dossier_notes"}}]
    )
    assert ok[0]["config"]["field"] == "dossier_notes"


def test_related_items_filters_by_relation_type_and_reads_issuer():
    from types import SimpleNamespace as NS
    from datetime import datetime

    issued = NS(
        eventtype=NS(title="Document Issued"),
        location=NS(title_ar=None, full_location=None, title="Branch 235"),
        from_date=datetime(2013, 5, 1),
    )
    doc = NS(
        id=1,
        deleted=False,
        title="Detention record",
        originid=None,
        sources=[],
        publish_date=None,
        documentation_date=None,
        events=[issued],
    )
    post = NS(**{**vars(doc), "id": 2, "title": "Facebook post", "events": []})
    actor = FakeActor()
    actor.related_bulletins = [
        NS(bulletin=doc, related_as=[1], comment=None),
        NS(bulletin=post, related_as=[14], comment=None),
    ]
    template = FakeTemplate(
        [
            {
                "type": "related_items_table",
                "config": {"relation_ids": [1], "columns": ["id", "issued_by"]},
            }
        ]
    )
    rows = build_dossier(template, actor, FakeUser())["blocks"][0]["rows"]
    assert [r["id"] for r in rows] == [1]
    assert rows[0]["issued_by"] == "Branch 235, 2013-05-01"


def test_field_table_formats_known_relatives():
    class Profile:
        known_relatives = [
            {"name": "Sara Doe", "relationship": "Sister", "phone": "0100 200 300"},
            # legacy entry written before the split fields existed
            {"name": "Ali Doe", "contact": "0100 200 300; Facebook: https://fb.com/ali"},
            {},
        ]

    actor = FakeActor()
    actor.actor_profiles = [Profile()]
    dossier = build_dossier(
        FakeTemplate([{"type": "field_table", "config": {"fields": ["known_relatives"]}}]),
        actor,
        FakeUser(),
    )
    (table,) = dossier["blocks"]
    value = table["rows"][0]["value"]
    assert [c["key"] for c in value["columns"]] == list(RELATIVE_FIELDS)
    assert [{k: v for k, v in r.items() if v} for r in value["rows"]] == [
        {"name": "Sara Doe", "relationship": "Sister", "phone": "0100 200 300"},
        {"name": "Ali Doe", "contact": "0100 200 300; Facebook: https://fb.com/ali"},
    ]
