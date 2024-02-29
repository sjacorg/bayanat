from uuid import uuid4
import pytest

from enferno.settings import TestConfig as cfg


@pytest.fixture(scope="session", autouse=True)
def flush_redis_after_tests():
    import redis
    import os

    yield
    # Code here will execute after all tests are done
    redis_dbs = [15, 14, 13, 12]
    for db in redis_dbs:
        r = redis.Redis(
            db=db,
            host=cfg.REDIS_HOST,
            port=cfg.REDIS_PORT,
            password=cfg.REDIS_PASSWORD,
        )
        r.flushdb()


@pytest.fixture(scope="session")
def app():
    from enferno.app import create_app
    from flask_login import FlaskLoginClient

    app = create_app(cfg)
    app.test_client_class = FlaskLoginClient
    with app.app_context():
        yield app


@pytest.fixture(scope="session")
def setup_db(app):
    from enferno.extensions import db as _db
    from enferno.utils.data_helpers import (
        generate_user_roles,
        generate_workflow_statues,
        create_default_location_data,
    )

    try:
        _db.engine.execute("CREATE EXTENSION if not exists pg_trgm ;")
        _db.engine.execute("CREATE EXTENSION if not exists postgis ;")
        _db.drop_all()
        _db.create_all()
        generate_user_roles()
        generate_workflow_statues()
        create_default_location_data()
    except Exception as e:
        pytest.skip(f"Test database setup failed, {e}")
    yield _db
    _db.session.remove()
    _db.drop_all()


@pytest.fixture(scope="function")
def session(setup_db, app):
    from enferno.extensions import db

    with app.app_context():
        with db.engine.begin() as conn:
            trans = conn.begin_nested()
            yield db.session
            trans.rollback()


@pytest.fixture(scope="function")
def users(session):
    from enferno.user.models import Role, User
    from enferno.admin.models import Activity

    admin_role = Role.query.filter(Role.name == "Admin").first()
    da_role = Role.query.filter(Role.name == "DA").first()
    mod_role = Role.query.filter(Role.name == "Mod").first()
    admin_user = User(username="TestAdmin", password="password", active=1)
    admin_user.roles.append(admin_role)
    admin_user.name = "Admin"
    admin_user.fs_uniquifier = uuid4().hex
    admin_user_sa = User(username="TestAdminSA", password="password", active=1)
    admin_user_sa.roles.append(admin_role)
    admin_user_sa.name = "AdminSA"
    admin_user_sa.can_self_assign = True
    admin_user_sa.fs_uniquifier = uuid4().hex
    da_user = User(username="TestDA", password="password", active=1)
    da_user.roles.append(da_role)
    da_user.name = "DA"
    da_user.fs_uniquifier = uuid4().hex
    da_user_sa = User(username="TestDASA", password="password", active=1)
    da_user_sa.roles.append(da_role)
    da_user_sa.name = "DASA"
    da_user_sa.can_self_assign = True
    da_user_sa.fs_uniquifier = uuid4().hex
    mod_user = User(username="TestMod", password="password", active=1)
    mod_user.roles.append(mod_role)
    mod_user.name = "Mod"
    mod_user.fs_uniquifier = uuid4().hex
    mod_user_sa = User(username="TestModSA", password="password", active=1)
    mod_user_sa.roles.append(mod_role)
    mod_user_sa.name = "ModSA"
    mod_user_sa.can_self_assign = True
    mod_user_sa.fs_uniquifier = uuid4().hex
    session.add(admin_user)
    session.add(da_user)
    session.add(mod_user)
    session.add(admin_user_sa)
    session.add(mod_user_sa)
    session.add(da_user_sa)
    session.commit()
    self_assign_dict = {}
    self_assign_dict["admin"] = admin_user_sa
    self_assign_dict["mod"] = mod_user_sa
    self_assign_dict["da"] = da_user_sa
    yield admin_user, da_user, mod_user, self_assign_dict
    user_ids = [admin_user.id, da_user.id, mod_user.id] + [
        user.id for user in self_assign_dict.values()
    ]
    session.query(Activity).filter(Activity.user_id.in_(user_ids)).delete(synchronize_session=False)
    session.delete(admin_user)
    session.delete(da_user)
    session.delete(mod_user)
    session.delete(admin_user_sa)
    session.delete(da_user_sa)
    session.delete(mod_user_sa)
    session.commit()


# test client for a user logged in as Admin role
@pytest.fixture(scope="function")
def admin_client(app, session, users):
    with app.app_context():
        admin_user, _, _, _ = users
        with app.test_client(user=admin_user) as client:
            yield client


# test client for a user logged in as DA role
@pytest.fixture(scope="function")
def da_client(app, session, users):
    with app.app_context():
        _, da_user, _, _ = users
        with app.test_client(user=da_user) as client:
            yield client


# test client for a user logged in as Mod role
@pytest.fixture(scope="function")
def mod_client(app, session, users):
    with app.app_context():
        _, _, mod_user, _ = users
        with app.test_client(user=mod_user) as client:
            yield client


# test client for an unauthenticated user
@pytest.fixture(scope="function")
def client(app, session):
    with app.app_context():
        with app.test_client() as client:
            yield client


# test client for admin that can self-assign
@pytest.fixture(scope="function")
def admin_sa_client(app, session, users):
    with app.app_context():
        _, _, _, sa_dict = users
        with app.test_client(user=sa_dict["admin"]) as client:
            yield client


# test client for da that can self-assign
@pytest.fixture(scope="function")
def da_sa_client(app, session, users):
    with app.app_context():
        _, _, _, sa_dict = users
        with app.test_client(user=sa_dict["da"]) as client:
            yield client


# test client for mod that can self-assign
@pytest.fixture(scope="function")
def mod_sa_client(app, session, users):
    with app.app_context():
        _, _, _, sa_dict = users
        with app.test_client(user=sa_dict["mod"]) as client:
            yield client
