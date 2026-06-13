from unittest.mock import MagicMock, patch

from enferno.tasks.maintenance import _strip_v


def test_strip_v_prefix():
    assert _strip_v("v4.1.0") == "4.1.0"
    assert _strip_v("4.1.0") == "4.1.0"
    assert _strip_v("") == ""


def _github_response(tag):
    return MagicMock(
        raise_for_status=lambda: None,
        json=lambda: {"tag_name": tag, "html_url": f"https://example/tag/{tag}"},
    )


def test_new_release_notifies_admins():
    """Update check is notify-only: a new tag caches the latest and notifies
    admins. It never triggers a privileged update (BAY-01-013)."""
    from enferno.tasks import maintenance

    fake_redis = MagicMock()
    fake_redis.get.return_value = None  # nothing notified yet
    with (
        patch.object(maintenance, "requests") as req,
        patch.object(maintenance, "rds", fake_redis),
        patch.object(maintenance, "_current_version", return_value="4.1.0"),
        patch.object(maintenance, "Notification") as notif,
    ):
        req.get.return_value = _github_response("v4.1.1")
        maintenance.check_for_updates.run()
        notif.create_for_admins.assert_called_once()


def test_same_version_does_not_notify():
    from enferno.tasks import maintenance

    fake_redis = MagicMock()
    fake_redis.get.return_value = None
    with (
        patch.object(maintenance, "requests") as req,
        patch.object(maintenance, "rds", fake_redis),
        patch.object(maintenance, "_current_version", return_value="4.1.1"),
        patch.object(maintenance, "Notification") as notif,
    ):
        req.get.return_value = _github_response("v4.1.1")
        maintenance.check_for_updates.run()
        notif.create_for_admins.assert_not_called()
