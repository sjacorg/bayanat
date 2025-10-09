"""Tests for dynamic field search filtering."""

from types import SimpleNamespace
from sqlalchemy.dialects import postgresql

from enferno.admin.models.DynamicField import DynamicField
from enferno.utils.search_utils import SearchUtils
import enferno.utils.search_utils as search_utils_module


class TestDynamicFieldSearch:
    """Test dynamic field filtering in search queries."""

    @staticmethod
    def _mock_db(fields, monkeypatch):
        """Mock database session with field metadata."""
        query_result = SimpleNamespace(filter=lambda *a, **k: SimpleNamespace(all=lambda: fields))
        session = SimpleNamespace(query=lambda *a, **k: query_result)
        monkeypatch.setattr(search_utils_module, "db", SimpleNamespace(session=session))

    @staticmethod
    def _make_field(name, field_type):
        """Create a mock dynamic field."""
        return SimpleNamespace(name=name, field_type=field_type, active=True, searchable=True)

    def test_select_field_any_operator_casts_values(self, monkeypatch):
        """Test SELECT field 'any' operator casts numeric values to varchar."""
        field = self._make_field("test_select", DynamicField.SELECT)
        self._mock_db([field], monkeypatch)

        conditions = []
        utils = SearchUtils([], "bulletin")
        utils._apply_dynamic_field_filters(
            conditions, {"dyn": [{"name": field.name, "op": "any", "value": [1, 2]}]}, "bulletin"
        )

        assert len(conditions) == 1
        sql = str(
            conditions[0].compile(
                dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
            )
        )

        # Verify CAST syntax, NULL check, and proper array operator
        assert "CAST(" in sql
        assert "AS varchar)" in sql
        assert "= ANY(test_select)" in sql
        assert "IS NOT NULL" in sql

    def test_text_field_contains_coerces_numeric(self, monkeypatch):
        """Test TEXT field 'contains' operator converts numeric values to strings."""
        field = self._make_field("test_text", DynamicField.TEXT)
        self._mock_db([field], monkeypatch)

        conditions = []
        utils = SearchUtils([], "bulletin")
        utils._apply_dynamic_field_filters(
            conditions, {"dyn": [{"name": field.name, "op": "contains", "value": 42}]}, "bulletin"
        )

        assert len(conditions) == 1
        bind_values = [p.value for p in conditions[0]._bindparams.values()]
        assert bind_values == ["%42%"]
