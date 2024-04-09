import pytest

from enferno.admin.models import Country
from tests.factories import CountryFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
    convert_empty_strings_to_none,
    get_first_or_fail,
)

#### PYDANTIC MODELS #####

from tests.models.admin import CountriesResponseModel

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_country(session):
    country = CountryFactory()
    session.add(country)
    session.commit()
    yield country
    try:
        session.query(Country).filter(Country.id == country.id).delete(synchronize_session=False)
        session.commit()
    except:
        pass


@pytest.fixture(scope="function")
def clean_slate_countries(session):
    session.query(Country).delete(synchronize_session=False)
    session.commit()
    yield


##### GET /admin/api/countries #####

countries_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", countries_endpoint_roles)
def test_countries_endpoint(
    clean_slate_countries, create_country, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/countries", headers={"Content-Type": "application/json"}, follow_redirects=True
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), CountriesResponseModel
        )


##### POST /admin/api/country #####

post_country_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_country_endpoint_roles)
def test_post_country(clean_slate_countries, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    country = CountryFactory()
    response = client_.post(
        "/admin/api/country",
        headers={"Content-Type": "application/json"},
        json={"item": country.to_dict()},
    )
    assert response.status_code == expected_status
    found_country = Country.query.filter(Country.title == country.title).first()
    if expected_status == 200:
        assert found_country
    else:
        assert found_country is None


##### PUT /admin/api/country/<int:id> #####

put_country_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_country_endpoint_roles)
def test_put_country(
    clean_slate_countries, create_country, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    country = get_first_or_fail(Country)
    country_id = country.id
    new_country = CountryFactory()
    new_country.id = country_id
    response = client_.put(
        f"/admin/api/country/{country_id}",
        headers={"Content-Type": "application/json"},
        json={"item": new_country.to_dict()},
    )
    assert response.status_code == expected_status
    found_country = Country.query.filter(Country.id == country_id).first()
    if expected_status == 200:
        assert found_country.title == new_country.title
    else:
        assert found_country.title != new_country.title


##### DELETE /admin/api/country/<int:id> #####

delete_country_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", delete_country_endpoint_roles)
def test_delete_country(
    clean_slate_countries, create_country, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    country = get_first_or_fail(Country)
    country_id = country.id
    response = client_.delete(
        f"/admin/api/country/{country_id}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_status
    found_country = Country.query.filter(Country.id == country_id).first()
    if expected_status == 200:
        assert found_country is None
    else:
        assert found_country
