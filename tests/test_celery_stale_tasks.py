# -*- coding: utf-8 -*-
"""Tests for stale-task defences: message expiry and missing-user guards."""

from sqlalchemy import func, select

from enferno.admin.models.Notification import Notification
from enferno.extensions import db
from enferno.tasks import ContextTask, celery


class TestMessageExpiry:
    def test_context_task_sets_expiry(self):
        assert ContextTask.expires == 24 * 60 * 60

    def test_expiry_applies_to_registered_tasks(self):
        # celery.Task is ContextTask, so every @celery.task inherits the bound
        task = celery.tasks["enferno.tasks.bulk_ops.bulk_update_actors"]
        assert task.expires == 24 * 60 * 60


class TestMissingUserGuard:
    def test_create_for_user_skips_missing_user(self, app, session):
        before = db.session.scalar(select(func.count()).select_from(Notification))

        result = Notification.create_for_user(None, "Bulk Operation Status", "message body")

        assert result is None
        after = db.session.scalar(select(func.count()).select_from(Notification))
        assert after == before, "a missing user must not write a notification row"
