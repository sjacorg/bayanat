"""
Test to verify that the current actor_query behavior matches pre-search-v4 behavior.
This test creates a replica of the pre-search-v4 actor_query implementation and compares
results with the current implementation to ensure behavior parity.
"""

import pytest
from sqlalchemy import or_, and_, func, select
from enferno.extensions import db
from enferno.admin.models import Actor, ActorProfile, Label, Source
from enferno.utils.search_utils import SearchUtils
from tests.factories import ActorFactory, ActorProfileFactory, LabelFactory, SourceFactory


class PreSearchV4ActorQuery:
    """Replica of the pre-search-v4 actor_query implementation for comparison."""

    def actor_query_pre_v4(self, q: dict) -> list:
        """
        Replica of pre-search-v4 actor_query method.
        Returns a list of query conditions (not a select statement).
        """
        query = []

        # Text search (pre-search-v4 style)
        tsv = q.get("tsv")
        if tsv:
            words = tsv.split(" ")
            qsearch = []

            for word in words:
                qsearch.append(
                    or_(
                        Actor.search.ilike(f"%{word}%"),
                        ActorProfile.search.ilike(f"%{word}%"),
                    )
                )

            subquery = db.session.query(Actor.id).join(Actor.actor_profiles).filter(*qsearch)
            query.append(Actor.id.in_(subquery))

        # Exclude filter (pre-search-v4 style)
        extsv = q.get("extsv")
        if extsv:
            words = extsv.split(" ")
            conditions = []

            for word in words:
                conditions.append(
                    or_(
                        Actor.search.ilike(f"%{word}%"),
                        ActorProfile.search.ilike(f"%{word}%"),
                    )
                )

            subquery = (
                db.session.query(Actor.id).join(Actor.actor_profiles).filter(or_(*conditions))
            )
            query.append(~Actor.id.in_(subquery))

        return query


class TestActorSearchBehavior:
    """Test class to verify actor search behavior parity."""

    @pytest.fixture(autouse=True)
    def setup_test_data(self, app, session):
        """Set up test data for search behavior comparison."""
        self.app = app
        self.db_session = session

        # Create test actors with profiles
        self.actor1 = ActorFactory(name="John Smith")
        session.add(self.actor1)
        session.flush()  # Get the ID
        self.profile1 = ActorProfileFactory(actor=self.actor1, description="Software Engineer")
        session.add(self.profile1)

        self.actor2 = ActorFactory(name="Jane Doe")
        session.add(self.actor2)
        session.flush()  # Get the ID
        self.profile2 = ActorProfileFactory(actor=self.actor2, description="Data Scientist")
        session.add(self.profile2)

        self.actor3 = ActorFactory(name="Bob Johnson")
        session.add(self.actor3)
        session.flush()  # Get the ID
        self.profile3 = ActorProfileFactory(actor=self.actor3, description="Project Manager")
        session.add(self.profile3)

        self.actor4 = ActorFactory(name="Alice Brown")
        session.add(self.actor4)
        session.flush()  # Get the ID
        self.profile4 = ActorProfileFactory(actor=self.actor4, description="Software Developer")
        session.add(self.profile4)

        session.commit()

        # Initialize search utilities
        self.search_utils = SearchUtils()
        self.pre_search_v4 = PreSearchV4ActorQuery()

    def get_actor_ids_from_current_query(self, search_query: dict) -> set:
        """Get actor IDs from current implementation."""
        stmt, conditions = self.search_utils.actor_query(search_query)

        # Execute the query and get IDs, then filter to only our test actors
        if conditions:
            result = self.db_session.execute(stmt)
            all_ids = {row.id for row in result.scalars()}
        else:
            # No conditions means all actors
            result = self.db_session.execute(select(Actor))
            all_ids = {row.id for row in result.scalars()}

        # Filter to only our test actors
        test_actor_ids = {self.actor1.id, self.actor2.id, self.actor3.id, self.actor4.id}
        return all_ids.intersection(test_actor_ids)

    def get_actor_ids_from_pre_v4_query(self, search_query: dict) -> set:
        """Get actor IDs from pre-search-v4 style implementation."""
        conditions = self.pre_search_v4.actor_query_pre_v4(search_query)

        # Execute the query and get IDs, then filter to only our test actors
        if conditions:
            stmt = select(Actor).where(and_(*conditions))
            result = self.db_session.execute(stmt)
            all_ids = {row.id for row in result.scalars()}
        else:
            # No conditions means all actors
            result = self.db_session.execute(select(Actor))
            all_ids = {row.id for row in result.scalars()}

        # Filter to only our test actors
        test_actor_ids = {self.actor1.id, self.actor2.id, self.actor3.id, self.actor4.id}
        return all_ids.intersection(test_actor_ids)

    def test_single_word_text_search(self):
        """Test single word text search behavior."""
        search_query = {"tsv": "John"}

        current_ids = self.get_actor_ids_from_current_query(search_query)
        v4_ids = self.get_actor_ids_from_pre_v4_query(search_query)

        assert (
            current_ids == v4_ids
        ), f"Single word search mismatch: current={current_ids}, v4={v4_ids}"

    def test_multi_word_text_search(self):
        """Test multi-word text search behavior - this is the critical test."""
        search_query = {"tsv": "Software Engineer"}

        current_ids = self.get_actor_ids_from_current_query(search_query)
        v4_ids = self.get_actor_ids_from_pre_v4_query(search_query)

        assert (
            current_ids == v4_ids
        ), f"Multi-word search mismatch: current={current_ids}, v4={v4_ids}"

        # Should find actors with BOTH "Software" AND "Engineer" in name or profile
        # This should only include "Software Engineer", not "Software Developer"
        expected_actors = {self.actor1.id}  # Only has both "Software" and "Engineer"
        assert current_ids == expected_actors, f"Expected {expected_actors}, got {current_ids}"

    def test_profile_only_search(self):
        """Test search that matches only in profile, not actor name."""
        search_query = {"tsv": "Scientist"}

        current_ids = self.get_actor_ids_from_current_query(search_query)
        v4_ids = self.get_actor_ids_from_pre_v4_query(search_query)

        assert current_ids == v4_ids, f"Profile search mismatch: current={current_ids}, v4={v4_ids}"
        assert current_ids == {self.actor2.id}, f"Expected {self.actor2.id}, got {current_ids}"

    def test_exclude_text_search_unquoted(self):
        """Test exclude text search without quotes (should use OR logic like pre-search-v4)."""
        search_query = {"extsv": "Software Engineer"}

        current_ids = self.get_actor_ids_from_current_query(search_query)
        v4_ids = self.get_actor_ids_from_pre_v4_query(search_query)

        assert current_ids == v4_ids, f"Exclude search mismatch: current={current_ids}, v4={v4_ids}"

        # Should exclude actors with "Software" OR "Engineer"
        # This should exclude both actor1 (Software Engineer) and actor4 (Software Developer)
        expected_actors = {self.actor2.id, self.actor3.id}  # Jane and Bob
        assert current_ids == expected_actors, f"Expected {expected_actors}, got {current_ids}"

    def test_exclude_text_search_quoted(self):
        """Test exclude text search with quotes (exact phrase matching)."""
        search_query = {"extsv": '"Software Engineer"'}

        current_ids = self.get_actor_ids_from_current_query(search_query)

        # Should exclude only exact phrase "Software Engineer"
        # This should exclude only actor1, not actor4 (Software Developer)
        expected_actors = {self.actor2.id, self.actor3.id, self.actor4.id}
        assert current_ids == expected_actors, f"Expected {expected_actors}, got {current_ids}"

    def test_empty_search(self):
        """Test empty search returns all actors."""
        search_query = {}

        current_ids = self.get_actor_ids_from_current_query(search_query)
        v4_ids = self.get_actor_ids_from_pre_v4_query(search_query)

        assert current_ids == v4_ids, f"Empty search mismatch: current={current_ids}, v4={v4_ids}"

        all_actor_ids = {self.actor1.id, self.actor2.id, self.actor3.id, self.actor4.id}
        assert (
            current_ids == all_actor_ids
        ), f"Expected all actors {all_actor_ids}, got {current_ids}"

    def test_no_match_search(self):
        """Test search with no matches."""
        search_query = {"tsv": "NonexistentTerm"}

        current_ids = self.get_actor_ids_from_current_query(search_query)
        v4_ids = self.get_actor_ids_from_pre_v4_query(search_query)

        assert (
            current_ids == v4_ids
        ), f"No match search mismatch: current={current_ids}, v4={v4_ids}"
        assert current_ids == set(), f"Expected empty set, got {current_ids}"

    def test_cross_field_search(self):
        """Test search that matches across actor name and profile description."""
        search_query = {"tsv": "John Manager"}

        current_ids = self.get_actor_ids_from_current_query(search_query)
        v4_ids = self.get_actor_ids_from_pre_v4_query(search_query)

        assert (
            current_ids == v4_ids
        ), f"Cross-field search mismatch: current={current_ids}, v4={v4_ids}"

        # Should find actors with BOTH "John" AND "Manager"
        # Bob Johnson has "John" in name (Johnson) and "Manager" in profile (Project Manager)
        expected_actors = {self.actor3.id}  # Bob Johnson matches both criteria
        assert current_ids == expected_actors, f"Expected {expected_actors}, got {current_ids}"

    def test_case_insensitive_search(self):
        """Test that search is case insensitive."""
        search_query = {"tsv": "JOHN"}

        current_ids = self.get_actor_ids_from_current_query(search_query)
        v4_ids = self.get_actor_ids_from_pre_v4_query(search_query)

        assert (
            current_ids == v4_ids
        ), f"Case insensitive search mismatch: current={current_ids}, v4={v4_ids}"
        # Should find actors with "JOHN" (case insensitive) - this includes "John" and "Johnson"
        expected_actors = {self.actor1.id, self.actor3.id}  # John Smith and Bob Johnson
        assert current_ids == expected_actors, f"Expected {expected_actors}, got {current_ids}"

    def test_partial_word_search(self):
        """Test partial word matching."""
        search_query = {"tsv": "Soft"}

        current_ids = self.get_actor_ids_from_current_query(search_query)
        v4_ids = self.get_actor_ids_from_pre_v4_query(search_query)

        assert (
            current_ids == v4_ids
        ), f"Partial word search mismatch: current={current_ids}, v4={v4_ids}"

        # Should find actors with "Soft" (Software)
        expected_actors = {self.actor1.id, self.actor4.id}
        assert current_ids == expected_actors, f"Expected {expected_actors}, got {current_ids}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
