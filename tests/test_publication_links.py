import pytest
from pydantic import ValidationError

from enferno.admin.validation.models import BulletinBulkModel
from tests.factories import BulletinFactory


def test_publication_links_accept_http_urls_only():
    url = "https://syriaaccountability.org/the-mechanics-of-foreign-surveillance/"
    assert BulletinBulkModel(publication_links=[f"  {url} ", url, ""]).publication_links == [url]
    assert BulletinBulkModel(publication_links=None).publication_links == []
    assert BulletinBulkModel(
        publication_links=["https:example.org/report", url]
    ).publication_links == ["https://example.org/report", url]
    for bad in (
        ["javascript:alert(1)"],
        ["syriaaccountability.org/report"],
        ["ftp://example.org/x"],
        [123],
        url,
    ):
        with pytest.raises(ValidationError):
            BulletinBulkModel(publication_links=bad)


def test_bulk_update_merges_publication_links(session, users):
    from enferno.tasks.bulk_ops import bulk_update_bulletins

    admin_user, _, _, _ = users
    first = "https://syriaaccountability.org/first/"
    second = "https://syriaaccountability.org/second/"
    b = BulletinFactory(publication_links=[first])
    session.add(b)
    session.commit()

    bulk_update_bulletins.run(
        [b.id], {"comments": "links", "publication_links": [second, first]}, admin_user.id
    )

    session.refresh(b)
    assert b.publication_links == [first, second]
    assert b.to_dict()["publication_links"] == [first, second]
