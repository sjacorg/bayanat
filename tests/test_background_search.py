# -*- coding: utf-8 -*-
"""Tests for the timeout-then-queue background search."""

import pytest
from psycopg2.errors import QueryCanceled
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from enferno.admin.models.Notification import Notification
from enferno.extensions import db
from enferno.tasks import background_search as run_background_search
from enferno.utils import background_search as bgs
from tests.factories import create_simple_bulletin  # noqa: F401


class TestStatementTimeout:
    def test_canceled_query_is_detected(self, app, session):
        db.session.execute(text("SET LOCAL statement_timeout = 50"))
        with pytest.raises(OperationalError) as exc:
            db.session.execute(text("SELECT pg_sleep(0.5)"))
        assert bgs.search_timed_out(exc.value)
        db.session.rollback()

    def test_other_errors_are_not_timeouts(self):
        assert not bgs.search_timed_out(ValueError("boom"))

    def test_apply_is_noop_when_disabled(self, app, session):
        # TestConfig sets SEARCH_TIMEOUT = 0; a long statement must run unbounded
        bgs.apply_search_timeout()
        db.session.execute(text("SELECT pg_sleep(0.1)"))
        db.session.rollback()


class TestResultStore:
    def test_round_trip_and_missing(self, app):
        bgs.store_result("tok-1", 7, "bulletin", [3, 2, 1])
        assert bgs.get_result("tok-1") == {"user_id": 7, "entity": "bulletin", "ids": [3, 2, 1]}
        assert bgs.get_result("missing-token") is None


class TestBackgroundSearchTask:
    def test_task_stores_ids_and_notifies(
        self, app, session, users, create_simple_bulletin  # noqa: F811
    ):
        admin_user, _, _, _ = users
        bulletin = create_simple_bulletin

        run_background_search.run("tok-task", admin_user.id, "bulletin", [{}])

        result = bgs.get_result("tok-task")
        assert result["user_id"] == admin_user.id
        assert bulletin.id in result["ids"]

        notification = (
            Notification.query.filter_by(user_id=admin_user.id)
            .order_by(Notification.id.desc())
            .first()
        )
        assert notification is not None
        assert "Search Completed" in notification.title
        assert "tok-task" in notification.message


class TestTimeoutFallbackEndpoint:
    def test_timed_out_search_returns_202_and_queues(self, admin_client, monkeypatch):
        def cancel(*args, **kwargs):
            raise OperationalError("canceled", None, QueryCanceled())

        monkeypatch.setattr("enferno.admin.views.bulletins.SearchUtils", cancel)
        queued = {}
        monkeypatch.setattr(
            "enferno.utils.background_search.queue_search",
            lambda user_id, entity, q: queued.update(entity=entity) or "tok-ep",
        )

        response = admin_client.post(
            "/admin/api/bulletins/", json={"q": [{"tsv": "needle"}], "per_page": 10}
        )

        assert response.status_code == 202
        assert response.json["queued"] is True
        assert response.json["token"] == "tok-ep"
        assert queued["entity"] == "bulletin"
