import pytest

from enferno.admin.validation.models import ConfigValidationModel
from enferno.app import s3_csp_origins


@pytest.mark.parametrize(
    "region",
    ["us-east-1", "eu-west-par", "EU-WEST-PAR", "gra", "fsn1", "auto", "us-east1", "my_region"],
)
def test_s3_compatible_region_names_are_accepted(region):
    assert ConfigValidationModel.validate_aws_region(region) == region


@pytest.mark.parametrize(
    "region", ["", "eu west", "eu-west/par", "https://s3.example.com", "a" * 65, None]
)
def test_malformed_region_names_are_rejected(region):
    assert ConfigValidationModel.validate_aws_region(region) is None


def test_csp_allows_aws_by_default(monkeypatch):
    monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("AWS_ENDPOINT_URL_S3", raising=False)
    assert s3_csp_origins("media", "eu-west-1") == [
        "https://media.s3.amazonaws.com",
        "https://media.s3.eu-west-1.amazonaws.com",
    ]


@pytest.mark.parametrize("var", ["AWS_ENDPOINT_URL", "AWS_ENDPOINT_URL_S3"])
def test_csp_follows_custom_endpoint(monkeypatch, var):
    monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("AWS_ENDPOINT_URL_S3", raising=False)
    monkeypatch.setenv(var, "https://s3.eu-west-par.io.cloud.ovh.net/")
    assert s3_csp_origins("media", "eu-west-par") == [
        "https://s3.eu-west-par.io.cloud.ovh.net",
        "https://media.s3.eu-west-par.io.cloud.ovh.net",
    ]
