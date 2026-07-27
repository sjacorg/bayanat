import pytest
from sqlalchemy import text

from enferno.extensions import db
from enferno.admin.models import Location, LocationAdminLevel, LocationType


@pytest.fixture
def tree(session):
    """Governorate > District > Subdistrict, three generations deep."""
    admin_type = LocationType.query.filter_by(title="Administrative Location").first()
    levels = {l.code: l for l in LocationAdminLevel.query.filter(LocationAdminLevel.code <= 3)}

    gov = Location(title="Aleppo", location_type=admin_type, admin_level=levels[1])
    session.add(gov)
    session.commit()
    dis = Location(title="Afrin", location_type=admin_type, admin_level=levels[2], parent_id=gov.id)
    session.add(dis)
    session.commit()
    sub = Location(
        title="Jandairis", location_type=admin_type, admin_level=levels[3], parent_id=dis.id
    )
    session.add(sub)
    session.commit()
    for l in (gov, dis, sub):
        l.rebuild_subtree()

    ids = [sub.id, dis.id, gov.id]
    yield gov.id, dis.id, sub.id
    session.query(Location).filter(Location.id.in_(ids)).delete(synchronize_session=False)
    session.commit()


def fetch(id):
    db.session.expire_all()
    return db.session.get(Location, id)


class TestSubtreeRebuild:
    def test_builds_the_whole_path(self, tree):
        gov_id, dis_id, sub_id = tree
        assert fetch(sub_id).full_location == "Aleppo, Afrin, Jandairis"
        assert fetch(sub_id).id_tree == f"[{sub_id}] [{dis_id}] [{gov_id}]"

    def test_rename_cascades_to_descendants(self, session, tree):
        gov_id, dis_id, sub_id = tree
        gov = fetch(gov_id)
        gov.title = "Aleppo Governorate"
        gov.save()
        gov.rebuild_subtree()

        assert fetch(dis_id).full_location == "Aleppo Governorate, Afrin"
        assert fetch(sub_id).full_location == "Aleppo Governorate, Afrin, Jandairis"

    def test_reparent_cascades_to_grandchildren(self, session, tree):
        """The serious case: descendants used to keep the old ancestor chain."""
        gov_id, dis_id, sub_id = tree
        admin_type = LocationType.query.filter_by(title="Administrative Location").first()
        other = Location(
            title="Idleb",
            location_type=admin_type,
            admin_level=LocationAdminLevel.query.filter_by(code=1).first(),
        )
        session.add(other)
        session.commit()
        other.rebuild_subtree()

        dis = fetch(dis_id)
        dis.parent_id = other.id
        dis.save()
        dis.rebuild_subtree()

        assert fetch(sub_id).full_location == "Idleb, Afrin, Jandairis"
        assert f"[{other.id}]" in fetch(sub_id).id_tree
        # and the moved grandchild is reachable from its new ancestor
        assert sub_id in Location.get_children_by_id(other.id)

        # put the branch back before dropping the temporary parent
        moved = fetch(dis_id)
        moved.parent_id = gov_id
        moved.save()
        session.query(Location).filter_by(id=other.id).delete(synchronize_session=False)
        session.commit()

    def test_leaves_the_rest_of_the_table_alone(self, session, tree):
        gov_id, _, _ = tree
        untouched = Location(title="Unrelated")
        session.add(untouched)
        session.commit()
        untouched.full_location = "Unrelated"
        untouched.id_tree = f"[{untouched.id}]"
        session.commit()

        fetch(gov_id).rebuild_subtree()

        assert fetch(untouched.id).full_location == "Unrelated"
        session.query(Location).filter_by(id=untouched.id).delete(synchronize_session=False)
        session.commit()


class TestStaleDetection:
    """
    The count is table wide, so these assert the delta this test causes rather
    than an absolute, which other test modules' fixtures would perturb.
    """

    def test_reports_nothing_for_rows_it_just_rebuilt(self, session, tree):
        _, _, sub_id = tree
        baseline = Location.count_stale_paths()
        db.session.get(Location, tree[0]).rebuild_subtree()
        assert Location.count_stale_paths() == baseline

    def test_detects_text_written_outside_the_app(self, session, tree):
        _, _, sub_id = tree
        baseline = Location.count_stale_paths()
        session.execute(
            text("update location set full_location = 'wrong' where id = :id"), {"id": sub_id}
        )
        session.commit()
        assert Location.count_stale_paths() == baseline + 1

    def test_detects_a_missing_ancestor_tree(self, session, tree):
        """An import that never generated id_tree leaves rows unreachable by ancestor search."""
        _, _, sub_id = tree
        baseline = Location.count_stale_paths()
        session.execute(text("update location set id_tree = null where id = :id"), {"id": sub_id})
        session.commit()
        assert Location.count_stale_paths() == baseline + 1
        assert sub_id not in Location.get_children_by_id(tree[0])


class TestRegenerateAll:
    def test_rebuilds_ancestor_trees_not_only_text(self, session, tree):
        """Regenerate used to fix the text and leave id_tree broken, with no way to repair it."""
        gov_id, dis_id, sub_id = tree
        session.execute(
            text("update location set id_tree = null, full_location = null where id = :id"),
            {"id": sub_id},
        )
        session.commit()

        Location.regenerate_all_full_locations()

        assert fetch(sub_id).id_tree == f"[{sub_id}] [{dis_id}] [{gov_id}]"
        assert fetch(sub_id).full_location == "Aleppo, Afrin, Jandairis"
        assert Location.count_stale_paths() == 0
