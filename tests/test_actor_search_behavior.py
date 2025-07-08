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
    """Test class to verify actor search behavior parity between current and pre-search-v4 implementations.

    For quoted exclude searches (extsv with quotes), we only test current implementation
    behavior since pre-v4 doesn't support quoted phrase exclusion. This is a new feature.

    For all other searches, we test both parity between implementations and verify that
    results match expected hardcoded ground truths.
    """

    @pytest.fixture(autouse=True)
    def setup_test_data(self, app, session):
        """Set up comprehensive test data with controlled inputs for predictable search behavior."""
        self.app = app
        self.db_session = session

        # Create test actors with controlled factory inputs to ensure predictable search fields
        # Actor.search = id + name + name_ar + comments
        # ActorProfile.search = id + originid + description + source_link

        # Basic test actors with minimal, controlled data
        self.actor1 = ActorFactory(name="John Smith", name_ar="", comments="")
        session.add(self.actor1)
        session.flush()
        self.profile1 = ActorProfileFactory(
            actor=self.actor1, description="Software Engineer", originid="", source_link=""
        )
        session.add(self.profile1)

        self.actor2 = ActorFactory(name="Jane Doe", name_ar="", comments="")
        session.add(self.actor2)
        session.flush()
        self.profile2 = ActorProfileFactory(
            actor=self.actor2, description="Data Scientist", originid="", source_link=""
        )
        session.add(self.profile2)

        self.actor3 = ActorFactory(name="Bob Johnson", name_ar="", comments="")
        session.add(self.actor3)
        session.flush()
        self.profile3 = ActorProfileFactory(
            actor=self.actor3, description="Project Manager", originid="", source_link=""
        )
        session.add(self.profile3)

        self.actor4 = ActorFactory(name="Alice Brown", name_ar="", comments="")
        session.add(self.actor4)
        session.flush()
        self.profile4 = ActorProfileFactory(
            actor=self.actor4, description="Software Developer", originid="", source_link=""
        )
        session.add(self.profile4)

        # Edge case actors with controlled special content
        self.actor5 = ActorFactory(
            name="María García-López", name_ar="ماريا", comments="UI Designer"
        )
        session.add(self.actor5)
        session.flush()
        self.profile5 = ActorProfileFactory(
            actor=self.actor5,
            description="UI/UX Designer & Artist",
            originid="MGL001",
            source_link="https://example.com/maria",
        )
        session.add(self.profile5)

        # Numeric and mixed content - controlled
        self.actor6 = ActorFactory(name="John Doe Jr. III", name_ar="", comments="Senior Executive")
        session.add(self.actor6)
        session.flush()
        self.profile6 = ActorProfileFactory(
            actor=self.actor6,
            description="CEO & Founder (2020-2024)",
            originid="JDJ003",
            source_link="https://company.com/ceo",
        )
        session.add(self.profile6)

        # SQL keywords - controlled
        self.actor7 = ActorFactory(name="SELECT FROM", name_ar="", comments="Database Expert")
        session.add(self.actor7)
        session.flush()
        self.profile7 = ActorProfileFactory(
            actor=self.actor7,
            description="Database Administrator",
            originid="SF001",
            source_link="https://db.com/admin",
        )
        session.add(self.profile7)

        # Whitespace test - controlled (cleaned up name)
        self.actor8 = ActorFactory(name="Whitespace Test", name_ar="", comments="QA Specialist")
        session.add(self.actor8)
        session.flush()
        self.profile8 = ActorProfileFactory(
            actor=self.actor8, description="Quality   Assurance", originid="WT001", source_link=""
        )
        session.add(self.profile8)

        # Long content - controlled
        self.actor9 = ActorFactory(
            name="VeryLongNameWithoutSpaces", name_ar="", comments="Long content specialist"
        )
        session.add(self.actor9)
        session.flush()
        self.profile9 = ActorProfileFactory(
            actor=self.actor9,
            description="This is a very long description that contains multiple words and should test how the search handles longer text content with various terms scattered throughout the description",
            originid="VLN001",
            source_link="https://longname.com",
        )
        session.add(self.profile9)

        # Case variations - controlled
        self.actor10 = ActorFactory(name="UPPERCASE Name", name_ar="", comments="case test")
        session.add(self.actor10)
        session.flush()
        self.profile10 = ActorProfileFactory(
            actor=self.actor10,
            description="lowercase description",
            originid="UP001",
            source_link="",
        )
        session.add(self.profile10)

        session.commit()

        # Initialize search utilities
        self.search_utils = SearchUtils()
        self.pre_search_v4 = PreSearchV4ActorQuery()

        # Store all test actor IDs for filtering
        self.all_test_actor_ids = {
            self.actor1.id,
            self.actor2.id,
            self.actor3.id,
            self.actor4.id,
            self.actor5.id,
            self.actor6.id,
            self.actor7.id,
            self.actor8.id,
            self.actor9.id,
            self.actor10.id,
        }

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

        return all_ids.intersection(self.all_test_actor_ids)

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

        return all_ids.intersection(self.all_test_actor_ids)

    def assert_search_parity(
        self, search_query: dict, expected_actors: set = None, test_name: str = ""
    ):
        """Helper method to assert search parity and optionally check expected results.

        Args:
            search_query: The search query to test
            expected_actors: Optional set of expected actor IDs. With controlled test data,
                           these should be hardcoded ground truths based on known content.
            test_name: Name for error messages

        This method ensures both current and pre-v4 implementations return the same results
        (parity testing) and optionally validates against expected hardcoded ground truths.
        """
        current_ids = self.get_actor_ids_from_current_query(search_query)
        v4_ids = self.get_actor_ids_from_pre_v4_query(search_query)

        assert current_ids == v4_ids, (
            f"{test_name} - Search parity mismatch: "
            f"current={current_ids}, v4={v4_ids}, query={search_query}"
        )

        if expected_actors is not None:
            assert current_ids == expected_actors, (
                f"{test_name} - Expected result mismatch: "
                f"expected={expected_actors}, got={current_ids}, query={search_query}"
            )

        return current_ids

    # ========== BASIC FUNCTIONALITY TESTS ==========

    def test_single_word_text_search(self):
        """Test single word text search behavior."""
        search_query = {"tsv": "John"}
        expected = {
            self.actor1.id,
            self.actor3.id,
            self.actor6.id,
        }  # John Smith, Bob Johnson, John Doe Jr. III
        self.assert_search_parity(search_query, expected, "Single word search")

    def test_multi_word_text_search(self):
        """Test multi-word text search behavior - this is the critical test."""
        search_query = {"tsv": "Software Engineer"}
        expected = {self.actor1.id}  # Only has both "Software" and "Engineer"
        self.assert_search_parity(search_query, expected, "Multi-word search")

    def test_profile_only_search(self):
        """Test search that matches only in profile, not actor name."""
        search_query = {"tsv": "Scientist"}
        expected = {self.actor2.id}  # Jane Doe - Data Scientist
        self.assert_search_parity(search_query, expected, "Profile-only search")

    def test_exclude_text_search_unquoted(self):
        """Test exclude text search without quotes (should use OR logic like pre-search-v4)."""
        search_query = {"extsv": "Software Engineer"}
        # Should exclude actors with "Software" OR "Engineer"
        excluded = {self.actor1.id, self.actor4.id}  # Software Engineer, Software Developer
        expected = self.all_test_actor_ids - excluded
        self.assert_search_parity(search_query, expected, "Exclude unquoted search")

    def test_exclude_text_search_quoted(self):
        """Test exclude text search with quotes (exact phrase matching).

        NOTE: Quoted exclude search is a new feature in current implementation.
        Pre-v4 doesn't support this, so we don't test for search parity.
        """
        search_query = {"extsv": '"Software Engineer"'}

        # Only test current implementation behavior (no parity check)
        current_ids = self.get_actor_ids_from_current_query(search_query)

        # Should exclude only exact phrase "Software Engineer"
        # This excludes actor1 (John Smith - Software Engineer)
        excluded = {self.actor1.id}
        expected = self.all_test_actor_ids - excluded

        assert current_ids == expected, (
            f"Exclude quoted search - Current implementation mismatch: "
            f"expected={expected}, got={current_ids}, query={search_query}"
        )

    def test_empty_search(self):
        """Test empty search returns all actors."""
        search_query = {}
        expected = self.all_test_actor_ids
        self.assert_search_parity(search_query, expected, "Empty search")

    def test_no_match_search(self):
        """Test search with no matches."""
        search_query = {"tsv": "NonexistentTermXYZ123"}
        expected = set()
        self.assert_search_parity(search_query, expected, "No match search")

    # ========== CROSS-FIELD AND COMPLEX SEARCH TESTS ==========

    def test_cross_field_search(self):
        """Test search that matches across actor name and profile description."""
        search_query = {"tsv": "John Manager"}
        # Bob Johnson has "John" in name (Johnson) and "Manager" in profile (Project Manager)
        expected = {self.actor3.id}
        self.assert_search_parity(search_query, expected, "Cross-field search")

    def test_three_word_search(self):
        """Test search with three words - all must match."""
        search_query = {"tsv": "John Doe Jr"}
        expected = {self.actor6.id}  # John Doe Jr. III
        self.assert_search_parity(search_query, expected, "Three word search")

    def test_partial_match_multi_word(self):
        """Test multi-word search where only some words match."""
        search_query = {"tsv": "John NonexistentWord"}
        expected = set()  # Both words must match
        self.assert_search_parity(search_query, expected, "Partial match multi-word")

    def test_combined_include_exclude_search(self):
        """Test using both tsv and extsv together."""
        search_query = {"tsv": "John", "extsv": "Smith"}
        # Include actors with "John", exclude actors with "Smith"
        # John Smith has both, so excluded. Bob Johnson and John Doe Jr. III have "John" but not "Smith"
        expected = {
            self.actor3.id,
            self.actor6.id,
        }  # Bob Johnson, John Doe Jr. III (not John Smith)
        self.assert_search_parity(search_query, expected, "Combined include/exclude")

    # ========== CASE SENSITIVITY TESTS ==========

    def test_case_insensitive_search(self):
        """Test that search is case insensitive."""
        search_query = {"tsv": "JOHN"}
        expected = {
            self.actor1.id,
            self.actor3.id,
            self.actor6.id,
        }  # John Smith, Bob Johnson, John Doe Jr. III
        self.assert_search_parity(search_query, expected, "Case insensitive search")

    def test_mixed_case_search(self):
        """Test mixed case search terms."""
        search_query = {"tsv": "SoFtWaRe"}
        expected = {self.actor1.id, self.actor4.id}  # Software Engineer, Software Developer
        self.assert_search_parity(search_query, expected, "Mixed case search")

    def test_uppercase_name_search(self):
        """Test searching for uppercase names."""
        search_query = {"tsv": "uppercase"}
        expected = {self.actor10.id}
        self.assert_search_parity(search_query, expected, "Uppercase name search")

    # ========== PARTIAL WORD AND SUBSTRING TESTS ==========

    def test_partial_word_search(self):
        """Test partial word matching."""
        search_query = {"tsv": "Soft"}
        expected = {self.actor1.id, self.actor4.id}  # Software Engineer, Software Developer
        self.assert_search_parity(search_query, expected, "Partial word search")

    def test_single_character_search(self):
        """Test single character search."""
        search_query = {"tsv": "a"}
        # Should match actors with 'a' in their search fields
        # Expected: María García-López, Jane Doe, Alice Brown, Database Admin, Quality Assurance, scattered, various
        expected = {
            self.actor1.id,  # John Smith - has 'a' in "Software Engineer"
            self.actor2.id,  # Jane Doe - has 'a' in "Jane"
            self.actor3.id,  # Bob Johnson - has 'a' in "Project Manager"
            self.actor4.id,  # Alice Brown - has 'a' in "Alice"
            self.actor5.id,  # María García-López - has 'a' in "María", "García"
            self.actor6.id,  # John Doe Jr. III - has 'a' in "https://company.com/ceo"
            self.actor7.id,  # SELECT FROM - has 'a' in "Database Administrator"
            self.actor8.id,  # Whitespace Test - has 'a' in "Quality Assurance"
            self.actor9.id,  # VeryLongName - has 'a' in "scattered", "various",
            self.actor10.id,  # UPPERCASE Name - has 'a' in "Name"
        }
        self.assert_search_parity(search_query, expected, "Single character search")

    def test_substring_in_middle_search(self):
        """Test searching for substring in middle of words."""
        search_query = {"tsv": "oft"}  # Should match "Software"
        expected = {self.actor1.id, self.actor4.id}  # Software Engineer, Software Developer
        self.assert_search_parity(search_query, expected, "Substring in middle search")

    # ========== SPECIAL CHARACTERS AND UNICODE TESTS ==========

    def test_unicode_search(self):
        """Test search with unicode characters."""
        search_query = {"tsv": "María"}
        expected = {self.actor5.id}
        self.assert_search_parity(search_query, expected, "Unicode search")

    def test_special_characters_search(self):
        """Test search with special characters."""
        search_query = {"tsv": "García-López"}
        expected = {self.actor5.id}
        self.assert_search_parity(search_query, expected, "Special characters search")

    def test_ampersand_search(self):
        """Test search with ampersand character."""
        search_query = {"tsv": "UI/UX"}
        expected = {self.actor5.id}
        self.assert_search_parity(search_query, expected, "Ampersand search")

    def test_parentheses_search(self):
        """Test search with parentheses."""
        search_query = {"tsv": "2020"}
        expected = {self.actor6.id}
        self.assert_search_parity(search_query, expected, "Parentheses content search")

    # ========== WHITESPACE HANDLING TESTS ==========

    def test_multiple_spaces_search(self):
        """Test search with multiple consecutive spaces."""
        search_query = {"tsv": "Software    Engineer"}  # Multiple spaces
        expected = {self.actor1.id}
        self.assert_search_parity(search_query, expected, "Multiple spaces search")

    def test_leading_trailing_spaces_search(self):
        """Test search with leading and trailing spaces."""
        search_query = {"tsv": "  Software Engineer  "}
        expected = {self.actor1.id}
        self.assert_search_parity(search_query, expected, "Leading/trailing spaces search")

    def test_tab_and_newline_search(self):
        """Test search with tab and newline characters."""
        search_query = {"tsv": "Software\tEngineer"}
        # Depending on implementation, tabs might be treated as word separators
        self.assert_search_parity(search_query, test_name="Tab character search")

    def test_whitespace_in_names_search(self):
        """Test searching for content with extra whitespace."""
        search_query = {"tsv": "Whitespace"}
        expected = {self.actor8.id}
        self.assert_search_parity(search_query, expected, "Whitespace in names search")

    def test_quality_assurance_spaces_search(self):
        """Test searching content with multiple spaces in profile."""
        search_query = {"tsv": "Quality Assurance"}
        expected = {self.actor8.id}
        self.assert_search_parity(search_query, expected, "Quality assurance spaces search")

    # ========== NUMERIC AND ALPHANUMERIC TESTS ==========

    def test_numeric_search(self):
        """Test search with numeric characters."""
        search_query = {"tsv": "2020"}
        expected = {self.actor6.id}
        self.assert_search_parity(search_query, expected, "Numeric search")

    def test_roman_numerals_search(self):
        """Test search with roman numerals."""
        search_query = {"tsv": "III"}
        expected = {self.actor6.id}
        self.assert_search_parity(search_query, expected, "Roman numerals search")

    def test_junior_abbreviation_search(self):
        """Test search with abbreviations."""
        search_query = {"tsv": "Jr"}
        expected = {self.actor6.id}
        self.assert_search_parity(search_query, expected, "Junior abbreviation search")

    # ========== SQL INJECTION PROTECTION TESTS ==========

    def test_sql_keywords_search(self):
        """Test search with SQL keywords."""
        search_query = {"tsv": "SELECT"}
        expected = {self.actor7.id}
        self.assert_search_parity(search_query, expected, "SQL keywords search")

    def test_sql_injection_attempt(self):
        """Test potential SQL injection strings."""
        search_query = {"tsv": "'; DROP TABLE actors; --"}
        expected = set()  # Should not match anything and not cause errors
        self.assert_search_parity(search_query, expected, "SQL injection attempt")

    def test_single_quote_search(self):
        """Test search with single quotes."""
        search_query = {"tsv": "O'Connor"}
        expected = set()  # No actor with this name
        self.assert_search_parity(search_query, expected, "Single quote search")

    # ========== LONG STRING AND PERFORMANCE TESTS ==========

    def test_very_long_search_term(self):
        """Test search with very long search terms."""
        long_term = "a" * 1000
        search_query = {"tsv": long_term}
        expected = set()  # Unlikely to match
        self.assert_search_parity(search_query, expected, "Very long search term")

    def test_long_name_search(self):
        """Test search in long names without spaces."""
        search_query = {"tsv": "VeryLong"}
        expected = {self.actor9.id}
        self.assert_search_parity(search_query, expected, "Long name search")

    def test_long_description_search(self):
        """Test search in long descriptions."""
        search_query = {"tsv": "scattered throughout"}
        expected = {self.actor9.id}
        self.assert_search_parity(search_query, expected, "Long description search")

    # ========== QUOTE HANDLING TESTS ==========

    def test_quoted_phrase_in_regular_search(self):
        """Test quoted phrases in regular search (not exclude)."""
        search_query = {"tsv": '"Software Engineer"'}
        # Implementation may or may not treat quotes specially in regular search
        self.assert_search_parity(search_query, test_name="Quoted phrase in regular search")

    def test_unmatched_quotes_search(self):
        """Test search with unmatched quotes."""
        search_query = {"tsv": '"Software Engineer'}
        self.assert_search_parity(search_query, test_name="Unmatched quotes search")

    def test_nested_quotes_search(self):
        """Test search with nested quotes."""
        search_query = {"tsv": '""Software""'}
        self.assert_search_parity(search_query, test_name="Nested quotes search")

    # ========== EDGE CASE VALUE TESTS ==========

    def test_none_values(self):
        """Test behavior with None values."""
        search_query = {"tsv": None}
        expected = self.all_test_actor_ids  # None should be treated like empty
        self.assert_search_parity(search_query, expected, "None values search")

    def test_empty_string_values(self):
        """Test behavior with empty string values."""
        search_query = {"tsv": ""}
        expected = self.all_test_actor_ids  # Empty string should return all
        self.assert_search_parity(search_query, expected, "Empty string values search")

    def test_whitespace_only_search(self):
        """Test search with only whitespace."""
        search_query = {"tsv": "   "}
        expected = self.all_test_actor_ids  # Whitespace-only should return all
        self.assert_search_parity(search_query, expected, "Whitespace-only search")

    def test_quoted_vs_unquoted_exclude_behavior(self):
        """Test to document the difference between quoted and unquoted exclude searches."""
        # Unquoted exclude (should have parity with pre-v4)
        unquoted_query = {"extsv": "Software Engineer"}
        unquoted_current = self.get_actor_ids_from_current_query(unquoted_query)
        unquoted_v4 = self.get_actor_ids_from_pre_v4_query(unquoted_query)

        # Should have parity - excludes actors with "Software" OR "Engineer"
        assert unquoted_current == unquoted_v4, (
            f"Unquoted exclude should have parity: " f"current={unquoted_current}, v4={unquoted_v4}"
        )

        # Quoted exclude (new feature, no parity expected)
        quoted_query = {"extsv": '"Software Engineer"'}
        quoted_current = self.get_actor_ids_from_current_query(quoted_query)

        # Quoted should exclude fewer actors than unquoted (only exact phrase)
        # This documents that quoted exclude is more precise
        assert len(quoted_current) >= len(unquoted_current), (
            f"Quoted exclude should exclude fewer actors than unquoted: "
            f"quoted_results={len(quoted_current)}, unquoted_results={len(unquoted_current)}"
        )

    # ========== COMPLEX EXCLUDE TESTS ==========

    def test_multi_word_exclude(self):
        """Test multi-word exclude search."""
        search_query = {"extsv": "Software Developer"}
        # Should exclude actors with "Software" OR "Developer"
        excluded = {self.actor1.id, self.actor4.id}  # Both have "Software", actor4 has "Developer"
        expected = self.all_test_actor_ids - excluded
        self.assert_search_parity(search_query, expected, "Multi-word exclude")

    def test_exclude_with_quotes_and_spaces(self):
        """Test exclude with quoted phrases containing spaces.

        NOTE: Quoted exclude search is a new feature in current implementation.
        Pre-v4 doesn't support this, so we don't test for search parity.
        """
        search_query = {"extsv": '"Project Manager"'}

        # Only test current implementation behavior (no parity check)
        current_ids = self.get_actor_ids_from_current_query(search_query)

        # Should exclude only exact phrase "Project Manager"
        # This excludes actor3 (Bob Johnson - Project Manager)
        excluded = {self.actor3.id}
        expected = self.all_test_actor_ids - excluded

        assert current_ids == expected, (
            f"Exclude quoted with spaces - Current implementation mismatch: "
            f"expected={expected}, got={current_ids}, query={search_query}"
        )

    def test_exclude_unicode(self):
        """Test exclude with unicode characters."""
        search_query = {"extsv": "María"}
        excluded = {self.actor5.id}
        expected = self.all_test_actor_ids - excluded
        self.assert_search_parity(search_query, expected, "Exclude unicode")

    # ========== PERFORMANCE AND STRESS TESTS ==========

    def test_many_search_terms(self):
        """Test search with many terms."""
        search_query = {"tsv": "John Jane Bob Alice Software Data Project UI CEO Database"}
        # All terms must match, so likely no results
        expected = set()
        self.assert_search_parity(search_query, expected, "Many search terms")

    def test_repeated_search_terms(self):
        """Test search with repeated terms."""
        search_query = {"tsv": "John John John"}
        expected = {self.actor1.id, self.actor3.id, self.actor6.id}  # Same as single "John"
        self.assert_search_parity(search_query, expected, "Repeated search terms")

    # ========== BOUNDARY AND ERROR CONDITION TESTS ==========

    def test_search_only_punctuation(self):
        """Test search with only punctuation."""
        search_query = {"tsv": "!@#$%^&*()"}
        expected = set()
        self.assert_search_parity(search_query, expected, "Only punctuation search")

    def test_search_mixed_punctuation_words(self):
        """Test search mixing punctuation and words."""
        search_query = {"tsv": "CEO & Founder"}
        expected = {self.actor6.id}
        self.assert_search_parity(search_query, expected, "Mixed punctuation words search")

    def test_search_forward_slash(self):
        """Test search with forward slash."""
        search_query = {"tsv": "UI/UX"}
        expected = {self.actor5.id}
        self.assert_search_parity(search_query, expected, "Forward slash search")

    # ========== COMPREHENSIVE INTEGRATION TESTS ==========

    def test_comprehensive_search_scenario(self):
        """Test a comprehensive realistic search scenario."""
        # Search for software-related roles but exclude engineers
        search_query = {"tsv": "Software", "extsv": "Engineer"}
        expected = {self.actor4.id}  # Software Developer (not Engineer)
        self.assert_search_parity(search_query, expected, "Comprehensive scenario")

    def test_case_insensitive_exclude(self):
        """Test case insensitive exclude search."""
        search_query = {"extsv": "JOHN"}
        # Should exclude actors with "john" case-insensitively: John Smith, Bob Johnson, John Doe Jr. III
        excluded = {self.actor1.id, self.actor3.id, self.actor6.id}
        expected = self.all_test_actor_ids - excluded
        self.assert_search_parity(search_query, expected, "Case insensitive exclude")

    def test_complex_real_world_scenario(self):
        """Test complex real-world search scenario."""
        # Find people with management roles but not in software
        search_query = {"tsv": "Manager", "extsv": "Software"}
        expected = {self.actor3.id}  # Project Manager (not Software-related)
        self.assert_search_parity(search_query, expected, "Complex real-world scenario")

    # ========== OUTPUT VALIDATION TESTS ==========

    def test_result_set_immutability(self):
        """Test that search results are consistent across multiple calls."""
        search_query = {"tsv": "John"}

        result1 = self.get_actor_ids_from_current_query(search_query)
        result2 = self.get_actor_ids_from_current_query(search_query)
        result3 = self.get_actor_ids_from_pre_v4_query(search_query)

        assert result1 == result2 == result3, "Search results should be consistent across calls"

    def test_no_side_effects(self):
        """Test that searches don't have side effects on database state."""
        initial_count = self.db_session.query(Actor).count()

        # Run several searches
        self.get_actor_ids_from_current_query({"tsv": "John"})
        self.get_actor_ids_from_current_query({"extsv": "Software"})
        self.get_actor_ids_from_pre_v4_query({"tsv": "Manager"})

        final_count = self.db_session.query(Actor).count()
        assert initial_count == final_count, "Search operations should not modify database"
