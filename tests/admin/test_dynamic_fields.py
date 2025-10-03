"""
Minimal unit tests for DynamicField model functionality.
Tests basic model operations without creating actual database columns.
"""

import pytest
from enferno.admin.models.DynamicField import DynamicField
from enferno.utils.base import DatabaseException


class TestDynamicField:
    """Test DynamicField model functionality."""

    def test_create_text_field(self, session):
        """Test creating a text dynamic field (model only)."""
        field = DynamicField(
            name="test_simple_text",
            title="Test Simple Text",
            entity_type="bulletin",
            field_type=DynamicField.TEXT,
            ui_component=DynamicField.UIComponent.INPUT,
        )

        # Field should save successfully
        field.save()

        # Verify field exists in database
        saved_field = DynamicField.query.filter_by(name="test_simple_text").first()
        assert saved_field is not None
        assert saved_field.field_type == DynamicField.TEXT
        assert saved_field.entity_type == "bulletin"

        # Cleanup
        session.delete(field)
        session.commit()

    def test_field_validation(self, session):
        """Test field validation rules."""
        # Test invalid field name
        with pytest.raises(ValueError, match="Field name must be a valid Python identifier"):
            DynamicField(
                name="invalid-name",
                title="Invalid Name",
                entity_type="bulletin",
                field_type=DynamicField.TEXT,
            )

        # Test reserved field name
        with pytest.raises(ValueError, match="Field name 'id' is reserved"):
            DynamicField(
                name="id",
                title="Reserved Name",
                entity_type="bulletin",
                field_type=DynamicField.TEXT,
            )

    def test_different_field_types(self, session):
        """Test creating different field types (model only)."""
        field_configs = [
            (DynamicField.TEXT, DynamicField.UIComponent.INPUT, "test_text"),
            (DynamicField.LONG_TEXT, DynamicField.UIComponent.TEXTAREA, "test_long_text"),
            (DynamicField.NUMBER, DynamicField.UIComponent.NUMBER_INPUT, "test_number"),
            (
                DynamicField.SELECT,
                DynamicField.UIComponent.DROPDOWN,
                "test_select",
                [{"label": "Option 1", "value": "opt1"}],
            ),
            (DynamicField.DATETIME, DynamicField.UIComponent.DATE_PICKER, "test_datetime"),
        ]

        created_fields = []

        for config in field_configs:
            if len(config) == 4:
                field_type, ui_component, name, options = config
            else:
                field_type, ui_component, name = config
                options = []

            field = DynamicField(
                name=name,
                title=f"Test {name}",
                entity_type="bulletin",
                field_type=field_type,
                ui_component=ui_component,
                options=options,
            )

            # Should save without errors
            field.save()
            created_fields.append(field)

            # Verify correct type mapping
            assert field.field_type == field_type
            assert field.ui_component == ui_component

        # Cleanup
        for field in created_fields:
            session.delete(field)
        session.commit()

    def test_field_options(self, session):
        """Test field with options (select field)."""
        field = DynamicField(
            name="test_options_dropdown",
            title="Test Options Dropdown",
            entity_type="bulletin",
            field_type=DynamicField.SELECT,
            ui_component=DynamicField.UIComponent.DROPDOWN,
            options=[
                {"label": "Option 1", "value": "opt1"},
                {"label": "Option 2", "value": "opt2"},
            ],
        )

        field.save()
        session.commit()

        # Verify options are stored
        saved_field = DynamicField.query.filter_by(name="test_options_dropdown").first()
        assert len(saved_field.options) == 2
        assert saved_field.options[0]["label"] == "Option 1"
        assert saved_field.options[0]["value"] == "opt1"

        # Verify options have IDs after save
        assert saved_field.options[0].get("id") == 1
        assert saved_field.options[1].get("id") == 2

        # Cleanup
        session.delete(field)
        session.commit()

    def test_field_configuration(self, session):
        """Test field configuration JSONB fields."""
        field = DynamicField(
            name="test_field_config",
            title="Test Field Config",
            entity_type="bulletin",
            field_type=DynamicField.TEXT,
            ui_component=DynamicField.UIComponent.INPUT,
            schema_config={"required": True, "default": "test"},
            ui_config={"help_text": "Enter text", "width": "w-100"},
            validation_config={"max_length": 100},
        )

        field.save()
        session.commit()

        # Verify configurations are stored
        saved_field = DynamicField.query.filter_by(name="test_field_config").first()
        assert saved_field.schema_config["required"] is True
        assert saved_field.ui_config["help_text"] == "Enter text"
        assert saved_field.validation_config["max_length"] == 100

        # Cleanup
        session.delete(field)
        session.commit()

    def test_field_uniqueness_constraint(self, session):
        """Test that field names must be unique per entity type."""
        # Create first field
        field1 = DynamicField(
            name="test_unique_name",
            title="Test Unique 1",
            entity_type="bulletin",
            field_type=DynamicField.TEXT,
            ui_component=DynamicField.UIComponent.INPUT,
        )
        field1.save()
        session.commit()

        # Try to create duplicate field name for same entity
        field2 = DynamicField(
            name="test_unique_name",  # Same name
            title="Test Unique 2",
            entity_type="bulletin",  # Same entity
            field_type=DynamicField.TEXT,
            ui_component=DynamicField.UIComponent.INPUT,
        )

        # DynamicField.save() doesn't pass through raise_exception, so we need to use the base save method
        with pytest.raises(DatabaseException):
            # Call the base class save method directly to access raise_exception parameter
            super(DynamicField, field2).save(raise_exception=True)

        # Cleanup
        session.delete(field1)
        session.commit()

    def test_get_valid_components(self, session):
        """Test getting valid UI components for field types."""
        # Test each field type has valid components
        assert DynamicField.UIComponent.INPUT in DynamicField.get_valid_components(
            DynamicField.TEXT
        )
        assert DynamicField.UIComponent.TEXTAREA in DynamicField.get_valid_components(
            DynamicField.LONG_TEXT
        )
        assert DynamicField.UIComponent.NUMBER_INPUT in DynamicField.get_valid_components(
            DynamicField.NUMBER
        )
        assert DynamicField.UIComponent.DROPDOWN in DynamicField.get_valid_components(
            DynamicField.SELECT
        )
        assert DynamicField.UIComponent.DATE_PICKER in DynamicField.get_valid_components(
            DynamicField.DATETIME
        )

        # Invalid field type should return empty list
        assert DynamicField.get_valid_components("invalid_type") == []

    def test_option_id_generation(self, session):
        """Test automatic option ID generation for select fields."""
        field = DynamicField(
            name="test_option_ids",
            title="Test Option IDs",
            entity_type="bulletin",
            field_type=DynamicField.SELECT,
            ui_component=DynamicField.UIComponent.DROPDOWN,
            options=[
                {"label": "Option A", "value": "opt_a"},
                {"label": "Option B", "value": "opt_b"},
            ],
        )

        # Initially no IDs
        assert field.options[0].get("id") is None
        assert field.options[1].get("id") is None

        # After save, IDs should be generated
        field.save()
        assert field.options[0].get("id") == 1
        assert field.options[1].get("id") == 2

        # Add new option - should get next ID
        field.options.append({"label": "Option C", "value": "opt_c"})
        field.ensure_option_ids()  # Call directly to test
        assert field.options[2].get("id") == 3

        # Delete middle option and add new one
        del field.options[1]  # Remove Option B (id=2)
        field.options.append({"label": "Option D", "value": "opt_d"})
        field.ensure_option_ids()  # Call directly to test

        # IDs should be: Option A=1, Option C=3, Option D=4 (not reusing 2)
        assert field.options[0].get("id") == 1  # Option A
        assert field.options[1].get("id") == 3  # Option C
        assert field.options[2].get("id") == 4  # Option D (new)

        # Cleanup
        session.delete(field)
        session.commit()

    def test_allow_multiple_config(self, session):
        """Test allow_multiple configuration for select fields."""
        # Create single-select field
        single_field = DynamicField(
            name="test_single_select",
            title="Test Single Select",
            entity_type="bulletin",
            field_type=DynamicField.SELECT,
            ui_component=DynamicField.UIComponent.DROPDOWN,
            schema_config={"allow_multiple": False},
            options=[{"label": "Option 1", "value": "opt1"}],
        )
        single_field.save()

        # Create multi-select field
        multi_field = DynamicField(
            name="test_multi_select",
            title="Test Multi Select",
            entity_type="bulletin",
            field_type=DynamicField.SELECT,
            ui_component=DynamicField.UIComponent.DROPDOWN,
            schema_config={"allow_multiple": True},
            options=[{"label": "Option 1", "value": "opt1"}],
        )
        multi_field.save()

        # Both should be SELECT type
        assert single_field.field_type == DynamicField.SELECT
        assert multi_field.field_type == DynamicField.SELECT

        # But different allow_multiple settings
        assert single_field.schema_config.get("allow_multiple") is False
        assert multi_field.schema_config.get("allow_multiple") is True

        # Cleanup
        session.delete(single_field)
        session.delete(multi_field)
        session.commit()
