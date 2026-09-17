"""
Tests for get_modified_date() on Actor, Bulletin and Incident.

The method returns the timestamp of the entity's most recent revision, falling
back to the entity's own updated_at when it has no revisions. It must do so
without loading the history collection: each revision carries a full JSON
snapshot in `data`, so materialising them to read one timestamp reads the
entire revision history of the entity.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import inspect

from tests.factories import (
    ActorFactory,
    ActorHistoryFactory,
    BulletinFactory,
    BulletinHistoryFactory,
    IncidentFactory,
    IncidentHistoryFactory,
)

BASE = datetime(2026, 1, 1, 12, 0, 0)


def _make(session, entity_factory, history_factory, fk, offsets):
    """Create an entity plus one revision per offset (in hours) from BASE."""
    entity = entity_factory()
    session.add(entity)
    session.flush()

    for offset in offsets:
        revision = history_factory(**{fk: entity.id})
        revision.created_at = BASE + timedelta(hours=offset)
        revision.updated_at = BASE + timedelta(hours=offset)
        session.add(revision)
    session.flush()

    return entity


# Each entry: entity factory, history factory, foreign key column on the history row.
ENTITIES = [
    pytest.param(ActorFactory, ActorHistoryFactory, "actor_id", id="actor"),
    pytest.param(BulletinFactory, BulletinHistoryFactory, "bulletin_id", id="bulletin"),
    pytest.param(IncidentFactory, IncidentHistoryFactory, "incident_id", id="incident"),
]


@pytest.mark.parametrize("entity_factory, history_factory, fk", ENTITIES)
class TestGetModifiedDate:
    def test_falls_back_to_updated_at_without_history(
        self, session, entity_factory, history_factory, fk
    ):
        entity = _make(session, entity_factory, history_factory, fk, offsets=[])

        assert entity.get_modified_date() == entity.updated_at

    def test_returns_latest_revision_timestamp(self, session, entity_factory, history_factory, fk):
        entity = _make(session, entity_factory, history_factory, fk, offsets=[0, 1, 2])

        assert entity.get_modified_date() == BASE + timedelta(hours=2)

    def test_latest_wins_regardless_of_insertion_order(
        self, session, entity_factory, history_factory, fk
    ):
        """Revisions can be backdated via create_revision(created=...)."""
        entity = _make(session, entity_factory, history_factory, fk, offsets=[5, 1, 3])

        assert entity.get_modified_date() == BASE + timedelta(hours=5)

    def test_matches_the_history_collection(self, session, entity_factory, history_factory, fk):
        """Equivalence with reading the ordered collection's last element."""
        entity = _make(session, entity_factory, history_factory, fk, offsets=[0, 4, 2])

        expected = entity.history[-1].updated_at if entity.history else entity.updated_at

        assert entity.get_modified_date() == expected

    def test_does_not_load_the_history_collection(
        self, session, entity_factory, history_factory, fk
    ):
        """Regression guard: loading `history` pulls every revision's data blob."""
        entity = _make(session, entity_factory, history_factory, fk, offsets=[0, 1, 2])
        session.expire(entity)

        entity.get_modified_date()

        assert "history" in inspect(entity).unloaded
