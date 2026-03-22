"""
Thin pytest configuration. Keeps the proven savepoint isolation pattern,
drops factory-boy, Pydantic schemas, and per-role fixture explosion.
"""

from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from enferno.app import create_app
from enferno.settings import TestConfig as cfg


# ---------------------------------------------------------------------------
# Session display
# ---------------------------------------------------------------------------


def pytest_sessionstart(session):
    terminal = session.config.pluginmanager.getplugin("terminalreporter")
    if terminal:
        terminal.write_line("")
        terminal.write_line("TEST CONFIG:", bold=True, yellow=True)
        terminal.write_line(f"  DB: {cfg.SQLALCHEMY_DATABASE_URI}", green=True)
        terminal.write_line(f"  Redis: {cfg.REDIS_HOST}:{cfg.REDIS_PORT}", green=True)
        terminal.write_line("")


# ---------------------------------------------------------------------------
# Redis cleanup
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def flush_redis_after_tests():
    import redis

    yield
    for db_num in (15, 14, 13, 12):
        r = redis.Redis(
            db=db_num,
            host=cfg.REDIS_HOST,
            port=cfg.REDIS_PORT,
            password=cfg.REDIS_PASSWORD,
        )
        r.flushdb()


# ---------------------------------------------------------------------------
# App fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def app():
    from flask_login import FlaskLoginClient

    app = create_app(cfg)
    app.test_client_class = FlaskLoginClient
    with app.app_context():
        with patch("enferno.setup.views.check_installation", return_value=False):
            yield app


# ---------------------------------------------------------------------------
# Database setup (session scope, runs once)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def setup_db(app):
    from enferno.extensions import db as _db
    from enferno.utils.data_helpers import (
        create_default_location_data,
        generate_user_roles,
        generate_workflow_statues,
    )
    from enferno.utils.db_utils import ensure_sql_functions

    with _db.engine.connect() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.commit()
        except ProgrammingError:
            conn.rollback()

    ensure_sql_functions()
    _db.drop_all()
    _db.create_all()

    with _db.engine.connect() as conn:
        generate_user_roles()
        generate_workflow_statues()
        create_default_location_data()
        conn.execute(text("INSERT INTO id_number_types (id, title) VALUES (1, 'National ID');"))
        conn.commit()

    yield _db

    _db.session.remove()
    _db.drop_all()


# ---------------------------------------------------------------------------
# Flush Flask-Session between tests (prevents FlaskLoginClient session leakage)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_session_store(app, monkeypatch):
    """Give each test its own FakeRedis so FlaskLoginClient sessions never collide."""
    import fakeredis

    monkeypatch.setattr(app.session_interface, "client", fakeredis.FakeStrictRedis())


# ---------------------------------------------------------------------------
# Per-test session with savepoint rollback
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def session(setup_db, app):
    """Each test gets a savepoint that auto-rolls-back. Zero cleanup needed."""
    from enferno.extensions import db

    with app.app_context():
        with db.engine.connect() as connection:
            with connection.begin():
                db.session.configure(bind=connection)
                with connection.begin_nested():
                    yield db.session
                db.session.remove()


# ---------------------------------------------------------------------------
# Test users (function scope, rolled back per test)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def users(session):
    """Create all test users. Returns dict keyed by role name."""
    from enferno.user.models import Role, User

    roles = {r.name: r for r in Role.query.all()}

    def make_user(username, role_name, can_self_assign=False):
        u = User(
            username=username,
            password="password",
            active=1,
            name=username,
            fs_uniquifier=uuid4().hex,
        )
        u.roles.append(roles[role_name])
        if can_self_assign:
            u.can_self_assign = True
        session.add(u)
        return u

    result = {
        "admin": make_user("TestAdmin", "Admin"),
        "admin_sa": make_user("TestAdminSA", "Admin", can_self_assign=True),
        "da": make_user("TestDA", "DA"),
        "da_sa": make_user("TestDASA", "DA", can_self_assign=True),
        "mod": make_user("TestMod", "Mod"),
        "mod_sa": make_user("TestModSA", "Mod", can_self_assign=True),
    }

    # TestRole + user for role-based access control tests
    test_role = Role(name="TestRole", description="Test")
    session.add(test_role)
    session.flush()
    roled_user = User(
        username="TestRoled",
        password="password",
        active=1,
        name="TestRoled",
        fs_uniquifier=uuid4().hex,
    )
    roled_user.roles.append(test_role)
    session.add(roled_user)
    result["roled"] = roled_user
    result["_test_role"] = test_role

    session.commit()
    return result


# ---------------------------------------------------------------------------
# Client helper (replaces 8+ named client fixtures)
# ---------------------------------------------------------------------------


def client_for(app, user=None):
    """
    Create a test client for a specific user, or anonymous if user=None.

    Usage in tests:
        with client_for(app, users["admin"]) as c:
            resp = c.get("/admin/api/something")

        with client_for(app) as c:  # anonymous
            resp = c.get("/admin/api/something")
    """
    if user:
        return app.test_client(user=user)
    else:
        from flask.testing import FlaskClient

        return FlaskClient(app)


def assert_status(app, users, method, url, role_status, **kwargs):
    """
    Assert expected status codes for each role.

    role_status: dict like {"admin": 200, "da": 403, "mod": 200, "anon": 401}
    kwargs: passed to client method (json=, headers=, etc.)
    """
    if "headers" not in kwargs:
        kwargs["headers"] = {"Content-Type": "application/json"}

    for role, expected in role_status.items():
        user = users.get(role)  # None for "anon"
        with client_for(app, user) as c:
            resp = getattr(c, method.lower())(url, **kwargs)
            assert (
                resp.status_code == expected
            ), f"{method} {url} as {role}: expected {expected}, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Keep old-style client fixtures for backward compat during migration
# (tests can use either pattern)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def admin_client(app, session, users):
    with app.app_context():
        with client_for(app, users["admin"]) as c:
            yield c


@pytest.fixture(scope="function")
def da_client(app, session, users):
    with app.app_context():
        with client_for(app, users["da"]) as c:
            yield c


@pytest.fixture(scope="function")
def mod_client(app, session, users):
    with app.app_context():
        with client_for(app, users["mod"]) as c:
            yield c


@pytest.fixture(scope="function")
def anonymous_client(app, session):
    with app.app_context():
        with client_for(app) as c:
            yield c


@pytest.fixture(scope="function")
def admin_sa_client(app, session, users):
    with app.app_context():
        with client_for(app, users["admin_sa"]) as c:
            yield c


@pytest.fixture(scope="function")
def da_sa_client(app, session, users):
    with app.app_context():
        with client_for(app, users["da_sa"]) as c:
            yield c


@pytest.fixture(scope="function")
def mod_sa_client(app, session, users):
    with app.app_context():
        with client_for(app, users["mod_sa"]) as c:
            yield c


@pytest.fixture(scope="function")
def roled_client(app, session, users):
    with app.app_context():
        with client_for(app, users["roled"]) as c:
            yield c


@pytest.fixture(scope="function")
def create_test_role(session, users):
    return users["_test_role"]
