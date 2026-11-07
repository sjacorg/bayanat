import pytest
from sqlalchemy import text

from enferno.extensions import db
from enferno.admin.models import Location, LocationAdminLevel, LocationType


@pytest.fixture
def make(session):
    """Create committed locations and delete them on teardown, even when a test fails."""
    created = []

    def _make(title, level=None, parent_id=None):
        admin_type = LocationType.query.filter_by(title="Administrative Location").first()
        level = level and LocationAdminLevel.query.filter_by(code=level).first()
        loc = Location(
            title=title, location_type=admin_type, admin_level=level, parent_id=parent_id
        )
        session.add(loc)
        session.commit()
        created.append(loc.id)
        return loc

    yield _make
    session.rollback()
    session.execute(
        text("update location set parent_id = null where id = any(:ids)"), {"ids": created}
    )
    session.query(Location).filter(Location.id.in_(created)).delete(synchronize_session=False)
    session.commit()


@pytest.fixture
def tree(make):
    """Governorate > District > Subdistrict."""
    gov = make("Aleppo", 1)
    dis = make("Afrin", 2, gov.id)
    sub = make("Jandairis", 3, dis.id)
    Location.regenerate_all_full_locations(root_id=gov.id)
    return gov.id, dis.id, sub.id


def fetch(id):
    db.session.expire_all()
    return db.session.get(Location, id)


def test_builds_the_whole_path(tree):
    gov_id, dis_id, sub_id = tree
    assert fetch(sub_id).full_location == "Aleppo, Afrin, Jandairis"
    assert fetch(sub_id).id_tree == f"[{sub_id}] [{dis_id}] [{gov_id}]"


def test_rename_cascades_to_descendants(tree):
    gov_id, dis_id, sub_id = tree
    gov = fetch(gov_id)
    gov.title = "Aleppo Governorate"
    gov.save()
    Location.regenerate_all_full_locations(root_id=gov_id)

    assert fetch(dis_id).full_location == "Aleppo Governorate, Afrin"
    assert fetch(sub_id).full_location == "Aleppo Governorate, Afrin, Jandairis"


def test_move_cascades_to_grandchildren(make, tree):
    _, dis_id, sub_id = tree
    other = make("Idleb", 1)
    dis = fetch(dis_id)
    dis.parent_id = other.id
    dis.save()
    Location.regenerate_all_full_locations(root_id=dis_id)

    assert fetch(sub_id).full_location == "Idleb, Afrin, Jandairis"
    assert sub_id in Location.get_children_by_id(other.id)


def test_scoped_rebuild_leaves_other_locations_alone(session, make, tree):
    gov_id, _, _ = tree
    untouched = make("Unrelated")
    session.execute(
        text("update location set full_location = 'sentinel', id_tree = 'sentinel' where id = :id"),
        {"id": untouched.id},
    )
    session.commit()

    Location.regenerate_all_full_locations(root_id=gov_id)

    assert fetch(untouched.id).full_location == "sentinel"
    assert fetch(untouched.id).id_tree == "sentinel"


def test_rebuild_terminates_on_a_pre_existing_cycle(session, tree):
    gov_id, _, sub_id = tree
    session.execute(
        text("update location set parent_id = :sub where id = :gov"), {"sub": sub_id, "gov": gov_id}
    )
    session.commit()

    Location.regenerate_all_full_locations(root_id=gov_id)  # returns rather than spinning
