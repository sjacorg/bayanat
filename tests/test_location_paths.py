import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from enferno.extensions import db
from enferno.admin.models import Location, LocationAdminLevel, LocationHierarchy, LocationType


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

    def test_counts_rows_the_root_walk_never_reaches(self, session, tree):
        """Two rows pointing at each other are unreachable from any root, so the
        rooted walk never visits them and their stored paths cannot be correct."""
        gov_id, dis_id, sub_id = tree
        baseline = Location.count_stale_paths()

        session.execute(
            text("update location set parent_id = :sub where id = :dis"),
            {"sub": sub_id, "dis": dis_id},
        )
        session.commit()

        try:
            assert Location.count_stale_paths() >= baseline + 2
        finally:
            session.execute(
                text("update location set parent_id = :gov where id = :dis"),
                {"gov": gov_id, "dis": dis_id},
            )
            session.commit()


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


class TestParentCycles:
    """
    Nothing used to stop a location becoming a child of its own descendant, and
    rebuilding a subtree walks downward, so a cycle would recurse until the
    statement timed out. Label guards its tree the same way.
    """

    def test_a_location_cannot_be_its_own_parent(self, session, tree):
        gov_id, _, _ = tree
        gov = fetch(gov_id)
        gov.parent_id = gov.id
        try:
            assert "under itself" in (gov.placement_error() or "")
        finally:
            session.rollback()

    def test_a_location_cannot_move_under_its_own_descendant(self, session, tree):
        gov_id, _, sub_id = tree
        gov = fetch(gov_id)
        gov.parent_id = sub_id
        try:
            assert "under itself" in (gov.placement_error() or "")
        finally:
            session.rollback()

    def test_a_normal_move_is_not_a_cycle(self, session, tree):
        gov_id, dis_id, sub_id = tree
        sub = fetch(sub_id)
        sub.parent_id = gov_id
        try:
            assert sub.placement_error() is None
        finally:
            session.rollback()

    def test_the_api_refuses_a_cycle(self, session, admin_client, tree):
        gov_id, _, sub_id = tree
        gov = fetch(gov_id)
        payload = gov.to_dict()
        payload["parent"] = {"id": sub_id}
        resp = admin_client.put(
            f"/admin/api/location/{gov_id}",
            json={"item": payload},
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400

    def test_the_database_refuses_a_self_parent(self, session, tree):
        gov_id, _, _ = tree
        with pytest.raises(IntegrityError):
            session.execute(
                text("update location set parent_id = id where id = :id"), {"id": gov_id}
            )
        session.rollback()

    def test_rebuilding_a_pre_existing_cycle_terminates(self, session, tree):
        """Data that already contains a cycle must not hang the rebuild."""
        gov_id, dis_id, sub_id = tree
        session.execute(
            text("update location set parent_id = :sub where id = :gov"),
            {"sub": sub_id, "gov": gov_id},
        )
        session.commit()
        fetch(gov_id).rebuild_subtree()  # returns rather than spinning
        assert Location.count_stale_paths() >= 0

        session.execute(text("update location set parent_id = null where id = :id"), {"id": gov_id})
        session.commit()


class TestParentLevelOrder:
    """
    A parent must sit above its child on the ladder. Verified against real data
    first: all 10,965 parented administrative locations on prod2 already satisfy
    this, so enforcing it rejects nothing that exists.
    """

    def test_a_parent_on_the_same_level_is_refused(self, session, tree):
        gov_id, dis_id, _ = tree
        other = fetch(dis_id)
        sibling = Location(
            title="Azaz",
            location_type=other.location_type,
            admin_level=other.admin_level,
            parent_id=dis_id,
        )
        session.add(sibling)
        try:
            assert "level above" in (sibling.placement_error() or "")
        finally:
            session.rollback()

    def test_an_inverted_parent_is_refused(self, session, tree):
        gov_id, dis_id, sub_id = tree
        gov = fetch(gov_id)
        inverted = Location(
            title="Backwards",
            location_type=gov.location_type,
            admin_level=gov.admin_level,
            parent_id=sub_id,
        )
        session.add(inverted)
        try:
            assert "level above" in (inverted.placement_error() or "")
        finally:
            session.rollback()

    def test_a_skipped_rung_is_allowed(self, session, tree):
        """Partner datasets may legitimately omit a rung, so only order is enforced."""
        gov_id, _, sub_id = tree
        sub = fetch(sub_id)
        sub.parent_id = gov_id
        try:
            assert sub.placement_error() is None
        finally:
            session.rollback()


class TestStructuralOrderIsIndependentOfDisplay:
    """
    The Full Location text format panel lets an admin drag levels into any order to
    match an address system, and a small-to-large format is the exact reverse of
    Syria's. Structure must therefore not be derived from display_order.
    """

    def test_reversing_the_display_order_does_not_invalidate_the_tree(self, session, tree):
        gov_id, dis_id, sub_id = tree
        levels = LocationAdminLevel.in_hierarchy(None).order_by(LocationAdminLevel.code).all()
        original = {l.id: l.display_order for l in levels}

        # reverse the presentation order, as the drag-and-drop panel would
        LocationAdminLevel.reorder([l.id for l in reversed(levels)], None)
        session.expire_all()
        try:
            assert fetch(sub_id).placement_error() is None
            assert fetch(dis_id).placement_error() is None
        finally:
            for id, order in original.items():
                session.get(LocationAdminLevel, id).display_order = order
            session.commit()


@pytest.fixture
def through_a_poi(session):
    """A levelled root, an unlevelled point of interest, and a levelled node below it."""
    admin_type = LocationType.query.filter_by(title="Administrative Location").first()
    poi_type = LocationType.query.filter_by(title="Point of Interest").first()
    top_level = LocationAdminLevel.in_hierarchy(None).filter_by(code=1).first()
    deep_level = LocationAdminLevel.in_hierarchy(None).filter_by(code=2).first()

    top = Location(title="Levelled root", location_type=admin_type, admin_level=top_level)
    session.add(top)
    session.commit()
    poi = Location(title="A crossing", location_type=poi_type, parent_id=top.id)
    session.add(poi)
    session.commit()
    deep = Location(
        title="Levelled below the crossing",
        location_type=admin_type,
        admin_level=deep_level,
        parent_id=poi.id,
    )
    session.add(deep)
    session.commit()

    ids = [deep.id, poi.id, top.id]
    yield top.id, poi.id, deep.id, deep_level
    session.rollback()
    session.query(Location).filter(Location.id.in_(ids)).delete(synchronize_session=False)
    session.commit()


class TestUnlevelledIntermediate:
    """
    A point of interest between two administrative locations is a supported shape,
    so the ladder rules have to hold through it in both directions. Validating
    upward but not downward left the second case below reachable from the editor.
    """

    def test_the_shape_itself_is_valid(self, through_a_poi):
        _, _, deep_id, _ = through_a_poi
        assert fetch(deep_id).placement_error() is None

    def test_a_child_on_another_ladder_is_refused_through_it(self, session, through_a_poi):
        _, poi_id, _, _ = through_a_poi
        hierarchy = LocationHierarchy(title="Ladder for POI test")
        session.add(hierarchy)
        session.commit()
        partner_level = LocationAdminLevel(
            code=2, title="Partner rung", display_order=2, hierarchy_id=hierarchy.id
        )
        session.add(partner_level)
        session.commit()

        stray = Location(
            title="Partner node under a legacy crossing",
            location_type=LocationType.query.filter_by(title="Administrative Location").first(),
            admin_level=partner_level,
            parent_id=poi_id,
        )
        session.add(stray)
        try:
            assert "different hierarchy" in (stray.placement_error() or "")
        finally:
            session.rollback()
            session.query(LocationAdminLevel).filter_by(hierarchy_id=hierarchy.id).delete(
                synchronize_session=False
            )
            session.query(LocationHierarchy).filter_by(id=hierarchy.id).delete(
                synchronize_session=False
            )
            session.commit()

    def test_relevelling_the_root_onto_its_deep_rung_is_refused(self, session, through_a_poi):
        top_id, _, _, deep_level = through_a_poi
        top = fetch(top_id)
        top.admin_level = deep_level
        assert "at or above" in (top.placement_error() or "")
