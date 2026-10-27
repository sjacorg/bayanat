import pytest
from pydantic import ValidationError

from enferno.admin.validation.models import BulletinBulkModel
from tests.factories import BulletinFactory


def test_publication_link_accepts_http_urls_only():
    url = "https://syriaaccountability.org/the-mechanics-of-foreign-surveillance/"
    assert BulletinBulkModel(publication_link=f"  {url} ").publication_link == url
    assert BulletinBulkModel(publication_link="").publication_link is None
    for bad in (
        "javascript:alert(1)",
        "syriaaccountability.org/report",
        "ftp://example.org/x",
        123,
    ):
        with pytest.raises(ValidationError):
            BulletinBulkModel(publication_link=bad)


def test_bulk_update_sets_publication_link(session, users):
    from enferno.tasks.bulk_ops import bulk_update_bulletins

    admin_user, _, _, _ = users
    b = BulletinFactory()
    session.add(b)
    session.commit()

    url = "https://syriaaccountability.org/report/"
    bulk_update_bulletins.run([b.id], {"comments": "link", "publication_link": url}, admin_user.id)

    session.refresh(b)
    assert b.publication_link == url
    assert b.to_dict()["publication_link"] == url
