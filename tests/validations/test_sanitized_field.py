from pydantic import ValidationError
import pytest

from enferno.admin.validation.models import BulletinValidationModel
from tests.factories import BulletinFactory


def test_sanitized_field_is_str():
    bulletin = BulletinFactory()
    bulletin.description = "Hello, World!"
    model = BulletinValidationModel(**bulletin.to_dict())
    assert model.description == "Hello, World!"
    bulletin.description = 5
    with pytest.raises(ValidationError):
        BulletinValidationModel(**bulletin.to_dict())


def test_sanitized_field_with_html():
    bulletin = BulletinFactory()
    bulletin.description = "<script>alert('Hello, World!');</script>"
    model = BulletinValidationModel(**bulletin.to_dict())
    assert model.description == "alert('Hello, World!');"


def test_sanitized_field_with_allowed_tags():
    bulletin = BulletinFactory()
    bulletin.description = "<span>Hello, World!</span>"
    model = BulletinValidationModel(**bulletin.to_dict())
    assert model.description == "<span>Hello, World!</span>"
