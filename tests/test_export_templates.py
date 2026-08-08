"""Unit tests for the dossier export template block registry.

These are pure-function tests: block validation, sanitization, and dossier
building against lightweight fake entities (no database)."""

import pytest

from enferno.export.blocks import (
    MAX_BLOCKS,
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


def test_media_appendix_fails_closed():
    """Only redaction results are surfaced; bare originals are excluded and flagged."""
    from types import SimpleNamespace as NS

    original = NS(id=1, redaction=None)
    redacted = NS(
        id=2,
        redaction=NS(original_media_id=1, source_media_id=1),
        media_file="doc-redacted.jpg",
        media_file_type="image/jpeg",
        title="doc",
        title_ar="وثيقة",
    )
    bare = NS(id=3, redaction=None)
    bulletin = NS(id=75, deleted=False, medias=[original, redacted, bare])

    actor = FakeActor()
    actor.related_bulletins = [NS(bulletin=bulletin)]
    template = FakeTemplate([{"type": "media_appendix", "config": {}}])
    context = build_dossier(template, actor, FakeUser())

    block = context["blocks"][0]
    assert [m["file"] for m in block["media"]] == ["doc-redacted.jpg"]
    assert block["media"][0]["title"] == "وثيقة"
    assert any("no redacted rendition" in m for m in context["missing"])
